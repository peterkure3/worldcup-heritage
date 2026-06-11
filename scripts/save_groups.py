import json

with open('D:\\Github\\worldcup-heritage\\tmp_teams.json', encoding='utf-8') as f:
    teams_data = json.load(f)
teams = teams_data['teams']

with open('D:\\Github\\worldcup-heritage\\tmp_groups.json', encoding='utf-8') as f:
    groups_data = json.load(f)
groups = groups_data['groups']

# Build team map with flag URLs
team_map = {}
for idx, t in enumerate(teams, 1):
    iso2 = t.get('iso2', '').lower()
    # Handle flagcdn exceptions for non-standard ISO codes
    flagcdn_map = {'sco': 'gb-sct', 'eng': 'gb-eng'}
    flagcdn_code = flagcdn_map.get(iso2, iso2)
    flag_svg = f"/flags/{flagcdn_code}.svg" if flagcdn_code else ''
    flag_png = t.get('flag', '')
    team_map[str(idx)] = {
        'id': idx,
        'name': t['name_en'],
        'flag_svg': flag_svg,
        'flag_png': flag_png,
        'fifa_code': t.get('fifa_code', ''),
        'iso2': iso2,
    }

output = {'groups': []}

for g in sorted(groups, key=lambda x: x['name']):
    g_entry = {
        'name': g['name'],
        'teams': [],
        'standings': [],
    }
    for t_entry in g['teams']:
        tid = t_entry['team_id']
        info = team_map.get(tid, {'name': f'Unknown({tid})', 'flag_svg': '', 'flag_png': '', 'fifa_code': '', 'iso2': ''})
        standing = {
            'team_id': int(tid),
            'team_name': info['name'],
            'flag_svg': info['flag_svg'],
            'flag_png': info['flag_png'],
            'fifa_code': info['fifa_code'],
            'iso2': info['iso2'],
            'played': int(t_entry.get('mp', 0)),
            'won': int(t_entry.get('w', 0)),
            'drawn': int(t_entry.get('d', 0)),
            'lost': int(t_entry.get('l', 0)),
            'goals_for': int(t_entry.get('gf', 0)),
            'goals_against': int(t_entry.get('ga', 0)),
            'goal_diff': int(t_entry.get('gd', 0)),
            'points': int(t_entry.get('pts', 0)),
        }
        g_entry['teams'].append(info['name'])
        g_entry['standings'].append(standing)

    output['groups'].append(g_entry)

with open('D:\\Github\\worldcup-heritage\\artifacts\\groups.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Saved {len(output['groups'])} groups with {sum(len(g['teams']) for g in output['groups'])} teams")
