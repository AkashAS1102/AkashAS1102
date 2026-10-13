"""Generate profile SVGs from public GitHub metadata; no external card services."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
from html import escape
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
USERNAME = 'AkashAS1102'
QUERY = '''query($login:String!) { user(login:$login) {
  followers { totalCount }
  repositories(first:100,privacy:PUBLIC,ownerAffiliations:OWNER) {
    totalCount nodes { stargazerCount languages(first:10) { edges { size node { name } } } }
  }
  contributionsCollection {
    contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
  }
} }'''

def save(name, content, height, title):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" viewBox="0 0 960 {height}" role="img" aria-labelledby="title"><title id="title">{escape(title)}</title><rect x="1" y="1" width="958" height="{height-2}" rx="20" fill="#181825" stroke="#45475A"/>{content}</svg>\n'
    (ROOT / 'assets' / name).write_text(svg, encoding='utf-8')

def generate(data):
    if data.get('errors'):
        raise RuntimeError('GitHub returned GraphQL errors')
    user = data['data']['user']
    if not user:
        raise RuntimeError('GitHub user not found')
    repos = user['repositories']
    if repos['totalCount'] > len(repos['nodes']):
        raise RuntimeError('Repository pagination required before updating totals')
    calendar = user['contributionsCollection']['contributionCalendar']
    stats = [('Followers', user['followers']['totalCount'], '#89DCEB'),
             ('Public repos', repos['totalCount'], '#F5C2E7'),
             ('Repo stars', sum(r['stargazerCount'] for r in repos['nodes']), '#F9E2AF'),
             ('Contributions', calendar['totalContributions'], '#A6E3A1')]
    date = dt.datetime.now(dt.timezone.utc).date().isoformat()
    body = '<g font-family="Segoe UI,Arial,sans-serif"><rect x="28" y="33" width="68" height="68" rx="22" fill="#CBA6F7"/><text x="62" y="76" text-anchor="middle" font-size="26" font-weight="700" fill="#313244">AS</text><text x="119" y="57" font-size="27" fill="#CDD6F4" font-weight="600">Akash AS</text><text x="119" y="84" font-size="16" fill="#A6ADC8">github.com/AkashAS1102</text>'
    for i, (label, count, color) in enumerate(stats):
        x = 397 + i*136
        body += f'<rect x="{x}" y="31" width="125" height="78" rx="16" fill="{color}"/><text x="{x+62.5}" y="66" text-anchor="middle" font-size="26" font-weight="700" fill="#313244">{count}</text><text x="{x+62.5}" y="89" text-anchor="middle" font-size="12" fill="#45475A">{label}</text>'
    body += f'<text x="28" y="146" font-size="12" fill="#7F849C">GitHub snapshot · {date} UTC · contribution count covers the past year</text></g>'
    save('profile-stats.svg', body, 170, 'GitHub profile statistics: ' + ', '.join(f'{n}: {c}' for n,c,_ in stats))

    body = '<g font-family="Segoe UI,Arial,sans-serif"><text x="28" y="37" font-size="22" font-weight="600" fill="#CDD6F4">A year of building</text>'
    body += f'<text x="28" y="62" font-size="14" fill="#A6ADC8">{calendar["totalContributions"]} GitHub contributions in the past year · updated {date}</text></g>'
    palette = ['#262637','#45405F','#71618D','#A38BBF','#CBA6F7']
    max_count = max(d['contributionCount'] for w in calendar['weeks'] for d in w['contributionDays']) or 1
    for i, week in enumerate(calendar['weeks']):
        for day in week['contributionDays']:
            count = day['contributionCount']
            row = (dt.date.fromisoformat(day['date']).weekday()+1)%7
            level = 0 if count == 0 else min(4, 1 + int(3*count/max_count))
            body += f'<rect x="{29+i*17}" y="{82+row*17}" width="13" height="13" rx="3" fill="{palette[level]}"><title>{day["date"]}: {count} contributions</title></rect>'
    body += '<g font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="#7F849C"><text x="28" y="226">Every small step adds up.</text><text x="774" y="226">Less</text><text x="915" y="226">More</text></g>'
    for i,color in enumerate(palette):
        body += f'<rect x="{811+i*18}" y="215" width="13" height="13" rx="3" fill="{color}"/>'
    save('activity.svg',body,245,'GitHub contribution calendar over the past year')

    languages = {}
    for repo in repos['nodes']:
        for edge in repo.get('languages',{}).get('edges',[]):
            name = edge['node']['name']
            languages[name] = languages.get(name,0) + edge['size']
    if languages:
        ordered = sorted(languages.items(),key=lambda kv:kv[1],reverse=True)
        entries = ordered[:5]
        if len(ordered)>5:
            entries.append(('Other',sum(v for _,v in ordered[5:])))
        total = sum(languages.values())
        colors = ['#CBA6F7','#89DCEB','#F5C2E7','#A6E3A1','#FAB387','#F9E2AF']
        body = '<g font-family="Segoe UI,Arial,sans-serif"><text x="28" y="38" font-size="22" font-weight="600" fill="#CDD6F4">Languages across my public repositories</text><text x="28" y="64" font-size="13" fill="#7F849C">Share of code bytes reported by GitHub · includes public forks</text></g>'
        x=28
        for (name,size),color in zip(entries,colors):
            width=904*size/total
            body += f'<rect x="{x:.2f}" y="84" width="{width:.2f}" height="18" fill="{color}"/>'
            x+=width
        for i,((name,size),color) in enumerate(zip(entries,colors)):
            x=28+(i%3)*300; y=134+(i//3)*29
            body+=f'<circle cx="{x+5}" cy="{y-4}" r="5" fill="{color}"/><text x="{x+20}" y="{y}" font-family="Segoe UI,Arial,sans-serif" font-size="14" fill="#BAC2DE">{escape(name)} · {size/total*100:.1f}%</text>'
        save('languages.svg',body,185,'Language distribution across public repositories by code bytes')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path)
    parser.add_argument('--query-output', type=Path)
    args = parser.parse_args()
    if args.query_output:
        args.query_output.write_text(json.dumps({'query':QUERY,'variables':{'login':USERNAME}}),encoding='utf-8')
        return
    if args.input:
        data=json.loads(args.input.read_text(encoding='utf-8-sig'))
    else:
        token=os.environ['GH_TOKEN']
        request=urllib.request.Request('https://api.github.com/graphql',data=json.dumps({'query':QUERY,'variables':{'login':USERNAME}}).encode(),headers={'Authorization':f'Bearer {token}','Content-Type':'application/json','User-Agent':'akash-profile-stats'})
        with urllib.request.urlopen(request,timeout=30) as response:
            data=json.load(response)
    generate(data)

if __name__ == '__main__':
    main()
