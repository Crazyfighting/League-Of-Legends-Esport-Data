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
def get_filename_url_to_open(site: EsportsClient, filename, team=None, width=None):
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
            
            # 保存圖片
            team_image_path = os.path.join(team_image_dir, f'{team}.png')
            print(f"保存隊伍圖片到: {team_image_path}")
            
            try:
                urllib.request.urlretrieve(url, team_image_path)
                print(f"成功保存隊伍圖片: {team}")
                return f'/static/team_images/{team}.png'
            except Exception as e:
                print(f"保存隊伍圖片時出錯: {e}")
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
        return stage_cache[game_id]

    game_id = game_id.lower()
    
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
        stage = 'PlayIn'
        if stage not in printed_stages:
            print(f"找到 {stage}")
            printed_stages.add(stage)
        stage_cache[game_id] = stage
        return stage
    
    # 檢查是否為 MainEvent Round
    round_match = re.search(r'round\s*(\d+)', game_id)
    if round_match:
        stage = f'MainEvent Round {round_match.group(1)}'
        if stage not in printed_stages:
            print(f"找到 {stage}")
            printed_stages.add(stage)
        stage_cache[game_id] = stage
        return stage
    
    # 檢查其他階段
    for key, stage in stage_mapping.items():
        if key in game_id:
            # 確保 final 不會被 quarter 或 semi 覆蓋
            if key == 'final' and ('quarter' in game_id or 'semi' in game_id):
                continue
            if stage not in printed_stages:
                print(f"找到 {stage}")
                printed_stages.add(stage)
            stage_cache[game_id] = stage
            return stage
    
    # 如果都沒有匹配到，返回 Unknown
    stage = 'Unknown'
    if stage not in printed_stages:
        print(f"找到 {stage}")
        printed_stages.add(stage)
    stage_cache[game_id] = stage
    return stage

def game_results(request):
    site = EsportsClient("lol")
    tournaments = lp.get_tournaments('International', year=2024)
    if not tournaments:
        return render(request, 'game_results/game_results.html', {'matches': []})

    # 印出所有比賽名稱
    print("\n=== 所有可用的比賽 ===")
    for i, t in enumerate(tournaments):
        print(f"{i}: {t.name}")

    tournament = tournaments[3]
    tournament_name = tournament.name
    print(f"\n選定比賽：{tournament_name}")

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
        print("\n現有的隊伍圖片快取：")
        for team, path in team_image_cache.items():
            print(f"{team}: {path}")
    else:
        team_image_cache = {}

    # 查詢所有比賽資料
    broad_query = site.cargo_client.query(
        tables="ScoreboardGames=SG, ScoreboardPlayers=SP, Players=P, MatchScheduleGame=MSG, MatchSchedule=MS",
        join_on="SG.GameId=SP.GameId, SP.Link=P.OverviewPage, SG.GameId=MSG.GameId, MSG.MatchId=MS.MatchId, MSG.MVP=MS.MVP",
        fields="SG.Team1, SG.Team2, SP.Champion, SP.Role, SP.Team, P.Player=Player, SG.Winner, SG.Gamename, SG.GameId, SG.OverviewPage, MSG.MVP, SG.Team1Kills, SG.Team2Kills, SP.Kills, SP.Deaths, SP.Assists, SP.Runes, SP.SummonerSpells",
        where='SG.Tournament LIKE "Worlds 2024%" OR SG.Tournament LIKE "Worlds 2024 Play-In%"',
        order_by="SG.GameId ASC",
    )

    role_order = ["Top", "Jungle", "Mid", "Bot", "Support"]
    match_map = {}

    # 將查詢結果轉換為列表
    query_results = list(broad_query)
    print(f"\n總共獲取到 {len(query_results)} 條記錄")

    # 使用 set 來存儲唯一的遊戲ID和比賽名稱
    game_ids = set()
    tournament_names = set()
    teams = set()
    
    for row in query_results:
        game_ids.add(row['GameId'])
        tournament_names.add(row['OverviewPage'])
        teams.add(row['Team1'])
        teams.add(row['Team2'])

    print("\n找到的隊伍：")
    for team in sorted(teams):
        print(f"- {team}")

    print("\n找到的比賽階段：")
    for row in query_results:
        game_id = row["GameId"]
        tab = get_stage_from_gameid(game_id)
        print(f"GameId: {game_id}, Stage: {tab}")

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

    print("\n更新後的隊伍圖片快取：")
    for team, path in team_image_cache.items():
        print(f"{team}: {path}")

    # 寫回圖片快取
    with open(team_image_cache_path, "w", encoding="utf-8") as f:
        json.dump(team_image_cache, f, ensure_ascii=False, indent=2)

    # 統計每個階段的比賽數量
    stage_counts = {}
    for row in query_results:
        game_id = row["GameId"]
        tab = get_stage_from_gameid(game_id)
        stage_counts[tab] = stage_counts.get(tab, 0) + 1

    print("\n各階段比賽數量：")
    for stage, count in stage_counts.items():
        print(f"{stage}: {count} 場")
    
    for row in query_results:
        game_id = row["GameId"]
        gamename = row["Gamename"]
        tab = get_stage_from_gameid(game_id)
        
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


        tournament_info = f'{overview.split("/")[0]} - {tab} {gamename}'

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
                url = get_filename_url_to_open(site, filename)
                player_image_cache[player_name] = url
            else:
                player_image_cache[player_name] = ""

        if game_id not in match_map:
            # 決定勝方隊伍名稱
            winner_team = team1 if str(row["Winner"]) == "1" else team2
            match_map[game_id] = {
                "Tournament": tournament_info,
                "Team1": team1,
                "Team2": team2,
                "Team1Image": team_image_cache.get(team1, ""),
                "Team2Image": team_image_cache.get(team2, ""),
                "Tab": tab,
                "Winner": row["Winner"],
                "WinnerTeam": winner_team,
                "Team1Points": team1_points,
                "Team2Points": team2_points,
                "MVP": mvp_player,
                "Players1_by_role": {},
                "Players2_by_role": {}
            }

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
        # 從 Tournament 中提取 Game 編號
        game_number_match = re.search(r'Game (\d+)', match["Tournament"])
        match["GameNumber"] = int(game_number_match.group(1)) if game_number_match else 0

    # 標記每組對戰的最後一場
    group_to_games = defaultdict(list)
    for match in match_map.values():
        # 使用隊伍名稱和 Tournament 作為分組鍵
        group_key = f"{match['MatchGroup']}_{match['Tournament'].split(' - ')[0]}"
        group_to_games[group_key].append(match)

    print("\n=== 對戰分組資訊 ===")
    for group, games in group_to_games.items():
        print(f"\n分組: {group}")
        # 找出該系列賽中 Game 編號最大的場次
        max_game = max(games, key=lambda m: m["GameNumber"])
        for m in games:
            # 使用 get_stage_from_gameid 來獲取階段
            stage = get_stage_from_gameid(m["Tournament"])
            m["is_last_game_in_group"] = (m["GameNumber"] == max_game["GameNumber"])
            # 只有 QuarterFinals、SemiFinals 和 Finals 的最後一場使用動畫效果
            m["use_animation"] = m["is_last_game_in_group"] and stage in ["QuarterFinals", "SemiFinals", "Finals"]
            print(f"比賽: {m['Tournament']}")
            print(f"  Game編號: {m['GameNumber']}")
            print(f"  階段: {stage}")
            print(f"  是否最後一場: {m['is_last_game_in_group']}")
            print(f"  是否使用動畫: {m['use_animation']}")

    # 排序：tab → 對戰組合 → Game 名稱
    matches = sorted(
        match_map.values(),
        key=lambda m: (
            m["Tab"],
            m["MatchGroup"],
            m["Tournament"]
        )
    )

    print("\n=== 最終排序後的比賽 ===")
    for match in matches:
        print(f"階段: {match['Tab']}")
        print(f"對戰組合: {match['MatchGroup']}")
        print(f"比賽名稱: {match['Tournament']}")
        print(f"是否最後一場: {match['is_last_game_in_group']}")
        print(f"是否使用動畫: {match['use_animation']}")
        print(f"贏方隊伍: {match['WinnerTeam']}")
        print(f"隊伍1: {match['Team1']}")
        print(f"隊伍2: {match['Team2']}")
        print("---")

    # 寫回圖片快取
    with open(image_cache_path, "w", encoding="utf-8") as f:
        json.dump(player_image_cache, f, ensure_ascii=False, indent=2)

    return render(request, 'game_results/game_results.html', {
        'matches': matches,
        'role_order': role_order
    })
