import json

with open('D:\\Github\\worldcup-heritage\\tmp_teams.json', encoding='utf-8') as f:
    teams_data = json.load(f)
teams = teams_data['teams']

with open('D:\\Github\\worldcup-heritage\\tmp_groups.json', encoding='utf-8') as f:
    groups_data = json.load(f)
groups = groups_data['groups']

team_map = {}
for idx, t in enumerate(teams, 1):
    team_map[str(idx)] = t['name_en']

for g in sorted(groups, key=lambda x: x['name']):
    g_name = g['name']
    g_teams = []
    for t_entry in g['teams']:
        tid = t_entry['team_id']
        g_teams.append(team_map.get(tid, f'Unknown({tid})'))
    print(f"Group {g_name}: {' | '.join(g_teams)}")
