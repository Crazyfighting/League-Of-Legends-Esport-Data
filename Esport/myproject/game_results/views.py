import re
from pathlib import Path
import json
from django.shortcuts import render
from mwrogue.esports_client import EsportsClient
import leaguepedia_parser as lp
import urllib.request
import os
from django.conf import settings
from collections import defaultdict

# 定義 BASE_DIR
BASE_DIR = settings.BASE_DIR

CHAMPION_IMAGE_DIR = Path("champion")
def get_filename_url_to_open(site: EsportsClient, filename, team=None, player=None, width=None):
    try:
        print(f"\n嘗試獲取圖片: {filename}")
        response = site.client.api(
            action="query",
            format="json",
            titles=f"File:{filename}",
            prop="imageinfo",
            iiprop="url",
            iiurlwidth=width,
        )
        
        image_info = next(iter(response["query"]["pages"].values()))["imageinfo"][0]
        url = image_info["thumburl"] if width else image_info["url"]
        
        if team:
            # 確保目錄存在
            team_image_dir = os.path.join(BASE_DIR, 'static', 'team_images')
            os.makedirs(team_image_dir, exist_ok=True)
            
            # 保存隊伍圖片
            team_image_path = os.path.join(team_image_dir, f'{team}.png')
            print(f"保存隊伍圖片到: {team_image_path}")
            
            try:
                urllib.request.urlretrieve(url, team_image_path)
                print(f"成功保存隊伍圖片: {team}")
                return f'/static/team_images/{team}.png'
            except Exception as e:
                print(f"保存隊伍圖片時出錯: {e}")
                return None
        
        if player:
            # 確保目錄存在
            player_image_dir = os.path.join(BASE_DIR, 'static', 'player_images')
            os.makedirs(player_image_dir, exist_ok=True)
            
            # 保存選手圖片
            player_image_path = os.path.join(player_image_dir, f'{player}.png')
            print(f"保存選手圖片到: {player_image_path}")
            
            try:
                urllib.request.urlretrieve(url, player_image_path)
                print(f"成功保存選手圖片: {player}")
                return f'/static/player_images/{player}.png'
            except Exception as e:
                print(f"保存選手圖片時出錯: {e}")
                return None
                
        return url
    except Exception as e:
        print(f"獲取圖片時出錯: {e}")
        return None

def clean_champion_name(champion_name):
    """清理英雄名稱，去除非字母字符"""
    return re.sub(r'[^a-zA-Z]', '', champion_name)

def clean_rune_name(rune_name):
    """清理符文名稱，移除空白和特殊字符"""
    return re.sub(r'[^a-zA-Z]', '', rune_name)

def get_summoner_spell_path(spell_name):
    """獲取召喚師技能圖片路徑"""
    clean_spell = clean_rune_name(spell_name)
    return f'/static/summonerspells/Summoner{clean_spell}.png'

def get_rune_path(rune_name):
    """獲取符文圖片路徑"""
    clean_name = clean_rune_name(rune_name)
    return f'/static/runes/{clean_name}/{clean_name}.png'

def get_champion_path(champion_name):
    """獲取英雄圖片路徑"""
    clean_name = clean_champion_name(champion_name)
    return f'/static/champion/{clean_name}.png'

# 用於記錄已經印過的標識
printed_stages = set()
# 用於快取已解析的階段
stage_cache = {}

def get_stage_from_gameid(game_id):
    """根據遊戲ID判斷比賽階段"""
    # 如果已經快取過，直接返回
    if game_id in stage_cache:
        cached_stage = stage_cache[game_id]
        # 如果快取的是字串，轉換為字典格式
        if isinstance(cached_stage, str):
            stage = {
                'type': cached_stage,
                'format': None,
                'number': None,
                'display': cached_stage
            }
            stage_cache[game_id] = stage
            return stage
        return cached_stage

    game_id = game_id.lower()
    
    # 檢查是否為 Worlds Qualifying Series
    if 'worlds qualifying series' in game_id:
        stage = {
            'type': 'PlayIn',
            'format': None,
            'number': None,
            'display': 'PlayIn'
        }
        if stage['display'] not in printed_stages:
            print(f"找到 {stage['display']}")
            printed_stages.add(stage['display'])
        stage_cache[game_id] = stage
        return stage
    
    # 檢查是否為 tiebreaker
    if 'tiebreaker' in game_id:
        # 判斷是 Play-in 還是 Main Event 的 tiebreaker
        if 'play-in' in game_id or 'playin' in game_id:
            stage = {
                'type': 'PlayIn',
                'format': 'Tiebreaker',
                'number': None,
                'display': 'PlayIn Tiebreaker'
            }
        else:
            stage = {
                'type': 'MainEvent',
                'format': 'Tiebreaker',
                'number': None,
                'display': 'MainEvent Tiebreaker'
            }
        if stage['display'] not in printed_stages:
            print(f"找到 {stage['display']}")
            printed_stages.add(stage['display'])
        stage_cache[game_id] = stage
        return stage
    
    # 定義階段對應表
    stage_mapping = {
        'quarter': 'QuarterFinals',
        'qf': 'QuarterFinals',
        'semi': 'SemiFinals',
        'sf': 'SemiFinals',
        'final': 'Finals',
        'play-in': 'PlayIn',
        'playin': 'PlayIn'
    }
    
    # 先檢查是否為 Play-In
    if 'play-in' in game_id or 'playin' in game_id:
        stage = {
            'type': 'PlayIn',
            'format': None,
            'number': None,
            'display': 'PlayIn'
        }
        if stage['display'] not in printed_stages:
            print(f"找到 {stage['display']}")
            printed_stages.add(stage['display'])
        stage_cache[game_id] = stage
        return stage
    
    # 檢查是否為 MainEvent Round 或 Day
    round_match = re.search(r'main\s*event.*?round\s*(\d+)', game_id, re.IGNORECASE)
    day_match = re.search(r'main\s*event.*?day\s*(\d+)', game_id, re.IGNORECASE)
    
    if round_match:
        stage = {
            'type': 'MainEvent',
            'format': 'Round',
            'number': round_match.group(1),
            'display': f'MainEvent Round {round_match.group(1)}'
        }
        if stage['display'] not in printed_stages:
            print(f"找到 {stage['display']}")
            printed_stages.add(stage['display'])
        stage_cache[game_id] = stage
        return stage
    elif day_match:
        stage = {
            'type': 'MainEvent',
            'format': 'Day',
            'number': day_match.group(1),
            'display': f'MainEvent Day {day_match.group(1)}'
        }
        if stage['display'] not in printed_stages:
            print(f"找到 {stage['display']}")
            printed_stages.add(stage['display'])
        stage_cache[game_id] = stage
        return stage
    
    # 檢查其他階段
    for key, stage_name in stage_mapping.items():
        if key in game_id:
            # 確保 final 不會被 quarter 或 semi 覆蓋
            if key == 'final' and ('quarter' in game_id or 'semi' in game_id):
                continue
            stage = {
                'type': stage_name,
                'format': None,
                'number': None,
                'display': stage_name
            }
            if stage['display'] not in printed_stages:
                print(f"找到 {stage['display']}")
                printed_stages.add(stage['display'])
            stage_cache[game_id] = stage
            return stage
    
    # 如果都沒有匹配到，返回 Unknown
    stage = {
        'type': 'Unknown',
        'format': None,
        'number': None,
        'display': 'Unknown'
    }
    print(f"\n無法識別的 game_id: {game_id}")
    if stage['display'] not in printed_stages:
        print(f"找到 {stage['display']}")
        printed_stages.add(stage['display'])
    stage_cache[game_id] = stage
    return stage

def clean_image_path(path, is_team=False):
    if not path:
        return path
    # 如果是隊伍圖片，保持原有大小寫
    if is_team:
        return path
    # 其他圖片路徑轉換為小寫
    return path.lower()

def game_results(request):
    site = EsportsClient("lol")
    print("\n=== 開始獲取比賽資料 ===")
    print("嘗試獲取 2024 年的國際比賽...")
    tournaments = lp.get_tournaments('International', year=2021)
    print(f"獲取到的比賽數量: {len(tournaments) if tournaments else 0}")
    
    if tournaments:
        print("\n2024 年的比賽列表:")
        for t in tournaments:
            print(f"- {t.name}")
    
    if not tournaments:
        print("沒有找到 2024 年的比賽，嘗試獲取 2023 年的比賽...")
        tournaments = lp.get_tournaments('International', year=2023)
        print(f"2023 年獲取到的比賽數量: {len(tournaments) if tournaments else 0}")
        if tournaments:
            print("\n2023 年的比賽列表:")
            for t in tournaments:
                print(f"- {t.name}")
    
    if not tournaments:
        return render(request, 'game_results/game_results.html', {'matches': []})

    # 過濾出 Worlds 的比賽
    world_tournaments = [t for t in tournaments if "Worlds" in t.name]
    print(f"\n過濾後的 Worlds 比賽數量: {len(world_tournaments)}")
    print("找到的 Worlds 比賽:")
    for t in world_tournaments:
        print(f"- {t.name}")
    
    # 動態生成查詢條件
    tournament_conditions = []
    for t in world_tournaments:
        tournament_conditions.append(f'SG.Tournament LIKE "{t.name}%"')
    
    where_condition = ' OR '.join(tournament_conditions)
    print(f"\n生成的查詢條件: {where_condition}")

    # 載入圖片快取
    image_cache_path = os.path.join(BASE_DIR, "player_images.json")
    team_image_cache_path = os.path.join(BASE_DIR, "team_images.json")
    
    if os.path.exists(image_cache_path):
        with open(image_cache_path, "r", encoding="utf-8") as f:
            player_image_cache = json.load(f)
    else:
        player_image_cache = {}

    if os.path.exists(team_image_cache_path):
        with open(team_image_cache_path, "r", encoding="utf-8") as f:
            team_image_cache = json.load(f)
    else:
        team_image_cache = {}

    # 查詢所有比賽資料
    broad_query = site.cargo_client.query(
        tables="ScoreboardGames=SG, ScoreboardPlayers=SP, Players=P, MatchScheduleGame=MSG, MatchSchedule=MS",
        join_on="SG.GameId=SP.GameId, SP.Link=P.OverviewPage, SG.GameId=MSG.GameId, MSG.MatchId=MS.MatchId, MSG.MVP=MS.MVP",
        fields="SG.Team1, SG.Team2, SP.Champion, SP.Role, SP.Team, P.Player=Player, SG.Winner, SG.Gamename, MSG.GameId, SG.OverviewPage, MSG.MVP, SG.Team1Kills, SG.Team2Kills, SP.Kills, SP.Deaths, SP.Assists, SP.Runes, SP.SummonerSpells, MS.MatchDay, MSG.MatchId, SG.MatchId",
        where=where_condition,
        order_by="MSG.GameId ASC",
    )

    role_order = ["Top", "Jungle", "Mid", "Bot", "Support"]
    match_map = {}
    processed_game_ids = set()  # 用於追蹤已處理的 game_id

    # 將查詢結果轉換為列表
    query_results = list(broad_query)
    print(f"\n總共獲取到 {len(query_results)} 條記錄")

    # 使用 set 來存儲唯一的遊戲ID和比賽名稱
    game_ids = set()
    tournament_names = set()
    teams = set()
    
    print("\n=== 處理比賽資料 ===")
    print("\n=== Play-in 階段的 GameId ===")
    printed_matches = set()  # 用於追蹤已印出的比賽
    playin_matches = []

    for row in query_results:
        game_id = row['GameId']
        print(f"處理 GameId: {game_id}")  # 添加調試輸出
        stage = get_stage_from_gameid(game_id)
        if stage['type'] == 'PlayIn':
            # 創建比賽資訊的組合字串
            match_info = f"{game_id}_{row.get('Team1', 'N/A')}_{row.get('Team2', 'N/A')}"
            # 如果這個組合還沒印出過，就加入列表
            if match_info not in printed_matches:
                # 解析 GameId 的結構
                parts = game_id.split('_')
                round_num = 0
                series_num = 0
                game_num = 0
                
                # 檢查是否為 Worlds Qualifying Series
                is_qualifying = 'Worlds Qualifying Series' in game_id
                
                # 如果不是 Qualifying Series，解析數字
                if not is_qualifying and len(parts) >= 3:
                    try:
                        round_num = int(parts[-3])
                        series_num = int(parts[-2])
                        game_num = int(parts[-1])
                    except ValueError:
                        pass
                
                playin_matches.append({
                    'game_id': game_id,
                    'team1': row.get('Team1', 'N/A'),
                    'team2': row.get('Team2', 'N/A'),
                    'is_qualifying': is_qualifying,
                    'round_num': round_num,
                    'series_num': series_num,
                    'game_num': game_num
                })
                printed_matches.add(match_info)
        if game_id in processed_game_ids:
            continue
            
        processed_game_ids.add(game_id)
        game_ids.add(game_id)
        tournament_names.add(row['OverviewPage'])
        teams.add(row['Team1'])
        teams.add(row['Team2'])

        # 決定勝方隊伍名稱
        winner_team = row['Team1'] if str(row['Winner']) == '1' else row['Team2']
        match_map[game_id] = {
            "GameId": game_id,  # 確保加入 GameId
            "Tournament": f'{row["OverviewPage"].split("/")[0]} - {get_stage_from_gameid(game_id)["display"]} {row["Gamename"].split(" - ")[0]}',
            "Team1": row['Team1'],
            "Team2": row['Team2'],
            "Team1Image": team_image_cache.get(row['Team1'], ""),
            "Team2Image": team_image_cache.get(row['Team2'], ""),
            "Tab": get_stage_from_gameid(game_id)['display'],
            "Winner": row['Winner'],
            "WinnerTeam": winner_team,
            "Team1Points": row.get('Team1Kills'),
            "Team2Points": row.get('Team2Kills'),
            "MVP": row.get('MVP', ''),
            "DateTime": row.get('MatchDay', ''),
            "Players1_by_role": {},
            "Players2_by_role": {}
        }

    # 排序：先排 Worlds Qualifying Series，然後按照 Round、Series、Game 排序，最後是 Play-In Qualifiers
    playin_matches.sort(key=lambda x: (
        not ('Worlds Qualifying Series' in x['game_id']),  # Worlds Qualifying Series 排在最前面
        x['round_num'],
        x['series_num'],
        x['game_num'],
        'Play-In_Qualifiers' in x['game_id'] # Play-In Qualifiers 排在最下面
    ))

    # 印出排序後的結果
    for match in playin_matches:
        print(f"GameId: {match['game_id']}")
        print(f"Team1: {match['team1']}")
        print(f"Team2: {match['team2']}")
        print("---")

    for game_id in sorted(game_ids):
        tab = get_stage_from_gameid(game_id)

    # 獲取所有隊伍的圖片
    for team in teams:
        if team not in team_image_cache or team_image_cache[team] is None:
            filename = f"{team}logo square.png"
            print(f"\n嘗試獲取 {team} 的圖片")
            result = get_filename_url_to_open(site, filename, team)
            if result:
                team_image_cache[team] = result
                print(f"{team} 的圖片路徑: {result}")
            else:
                print(f"無法獲取 {team} 的圖片")

    # 寫回圖片快取
    with open(team_image_cache_path, "w", encoding="utf-8") as f:
        json.dump(team_image_cache, f, ensure_ascii=False, indent=2)

    # 統計每個階段的比賽數量
    stage_counts = {}
    for row in query_results:
        game_id = row["GameId"]
        stage = get_stage_from_gameid(game_id)
        stage_counts[stage['display']] = stage_counts.get(stage['display'], 0) + 1

    print("\n各階段比賽數量：")
    for stage, count in stage_counts.items():
        print(f"{stage}: {count/10} 場")
    
    for row in query_results:
        game_id = row["GameId"]
        gamename = row["Gamename"]
        stage = get_stage_from_gameid(game_id)
        
        player_name = row["Player"]
        role = row["Role"]
        champion = clean_champion_name(row["Champion"])
        team1 = row["Team1"]
        team2 = row["Team2"]
        player_team = row["Team"]
        overview = row["OverviewPage"]
        mvp_player = (row.get("MVP", "") or "").strip().lower()
        # 使用 ScoreboardGames 的 Team1Kills 和 Team2Kills
        team1_points = row.get("Team1Kills")
        team2_points = row.get("Team2Kills")
        # 獲取比賽日期
        match_day = row.get("MatchDay", "")

        tournament_info = f'{overview.split("/")[0]} - {stage["display"]} {gamename} {match_day}'

        # 抓選手圖片（快取）
        if player_name not in player_image_cache:
            r = site.cargo_client.query(
                limit=1,
                tables="PlayerImages=PI, Tournaments=T",
                fields="PI.FileName",
                join_on="PI.Tournament=T.OverviewPage",
                where=f'Link="{player_name}"',
                order_by="PI.SortDate DESC, T.DateStart DESC"
            )
            if r:
                filename = r[0]["FileName"]
                url = get_filename_url_to_open(site, filename, player=player_name)
                player_image_cache[player_name] = url
            else:
                player_image_cache[player_name] = ""

        match = match_map[game_id]

        safe_player_name = (player_name or "").strip().lower()
        is_mvp = safe_player_name == (match_map[game_id]["MVP"] or "")

        if player_team == match["Team1"]:
            # 處理符文和召喚師技能
            runes = row.get("Runes", "").split(",")[0] if row.get("Runes") else ""
            summoner_spells = row.get("SummonerSpells", "").split(",") if row.get("SummonerSpells") else []
            
            match["Players1_by_role"][role] = {
                "image": player_image_cache[player_name],
                "champion": get_champion_path(champion),
                "role": role,
                "name": player_name,
                "is_mvp": is_mvp,
                "kills": row.get("Kills", 0),
                "deaths": row.get("Deaths", 0),
                "assists": row.get("Assists", 0),
                "rune": get_rune_path(runes),
                "summoner_spells": [get_summoner_spell_path(spell.strip()) for spell in summoner_spells]
            }
            # 在終端機中顯示符文和召喚師技能資訊
        elif player_team == match["Team2"]:
            # 處理符文和召喚師技能
            runes = row.get("Runes", "").split(",")[0] if row.get("Runes") else ""
            summoner_spells = row.get("SummonerSpells", "").split(",") if row.get("SummonerSpells") else []
            
            match["Players2_by_role"][role] = {
                "image": player_image_cache[player_name],
                "champion": get_champion_path(champion),
                "role": role,
                "name": player_name,
                "is_mvp": is_mvp,
                "kills": row.get("Kills", 0),
                "deaths": row.get("Deaths", 0),
                "assists": row.get("Assists", 0),
                "rune": get_rune_path(runes),
                "summoner_spells": [get_summoner_spell_path(spell.strip()) for spell in summoner_spells]
            }
            # 在終端機中顯示符文和召喚師技能資訊

    # 加入對戰組合識別鍵
    for match in match_map.values():
        teams = sorted([match["Team1"], match["Team2"]])
        match["MatchGroup"] = f"{teams[0]} vs {teams[1]}"
        # 從 GameId 中提取系列賽資訊
        game_id = match["GameId"]
        match["SeriesId"] = game_id.split('_')[0]  # 取 GameId 的第一部分作為系列賽 ID
        
        # 解析 GameId 的結構
        parts = game_id.split('_')
        match["is_qualifying"] = 'Worlds Qualifying Series' in game_id
        match["round_num"] = 0
        match["series_num"] = 0
        match["game_num"] = 0
        
        if not match["is_qualifying"] and len(parts) >= 3:
            try:
                match["round_num"] = int(parts[-3])
                match["series_num"] = int(parts[-2])
                match["game_num"] = int(parts[-1])
            except ValueError:
                pass

    # 標記每組對戰的最後一場
    group_to_games = defaultdict(list)
    for match in match_map.values():
        # 使用隊伍名稱和 SeriesId 作為分組鍵
        group_key = f"{match['MatchGroup']}_{match['SeriesId']}"
        group_to_games[group_key].append(match)

    print("\n=== 對戰分組資訊 ===")
    for group, games in group_to_games.items():
        # 找出該系列賽中最後一場
        max_game = max(games, key=lambda m: m["GameId"])
        for m in games:
            # 使用 get_stage_from_gameid 來獲取階段
            stage = get_stage_from_gameid(m["GameId"])
            m["is_last_game_in_group"] = (m["GameId"] == max_game["GameId"])
            # 只有 QuarterFinals、SemiFinals 和 Finals 的最後一場使用動畫效果
            m["use_animation"] = m["is_last_game_in_group"] and stage['type'] in ["QuarterFinals", "SemiFinals", "Finals"]
            # 設置顯示用的階段名稱
            m["Tab"] = stage['display']
            # 設置階段格式和編號（用於 HTML 顯示）
            m["stage_format"] = stage['format']
            m["stage_number"] = stage['number']

    # 排序：tab → is_qualifying → round_num → series_num → game_num
    matches = sorted(
        match_map.values(),
        key=lambda m: (
            m["Tab"],
            not ('Worlds Qualifying Series' in m["GameId"]),  # Worlds Qualifying Series 排在最前面
            m["round_num"],
            m["series_num"],
            m["game_num"],
            'Play-In_Elimination' in m["GameId"],  # Elimination 排在 Qualifiers 之前
            not ('Play-In_Qualifiers' in m["GameId"])  # Qualifiers 排在最下面
        )
    )

    print("\n=== 最終排序後的比賽 ===")
    for match in matches:
        # 隊伍圖片保持原有大小寫
        match['Team1Image'] = clean_image_path(match['Team1Image'], is_team=True)
        match['Team2Image'] = clean_image_path(match['Team2Image'], is_team=True)
        
        # 其他圖片路徑轉換為小寫
        for player in list(match['Players1_by_role'].values()) + list(match['Players2_by_role'].values()):
            player['champion'] = clean_image_path(player['champion'])
            player['rune'] = clean_image_path(player['rune'])
            player['summoner_spells'] = [clean_image_path(spell) for spell in player['summoner_spells']]

    # 寫回圖片快取
    with open(image_cache_path, "w", encoding="utf-8") as f:
        json.dump(player_image_cache, f, ensure_ascii=False, indent=2)

    return render(request, 'game_results/game_results.html', {
        'matches': matches,
        'role_order': role_order
    })
