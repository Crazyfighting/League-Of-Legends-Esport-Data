import re
from pathlib import Path
import json
from django.shortcuts import render
from mwrogue.esports_client import EsportsClient
import leaguepedia_parser as lp

CHAMPION_IMAGE_DIR = Path("champion")
def get_filename_url_to_open(site: EsportsClient, filename, width=None):
    response = site.client.api(
        action="query",
        format="json",
        titles=f"File:{filename}",
        prop="imageinfo",
        iiprop="url",
        iiurlwidth=width,
    )
    image_info = next(iter(response["query"]["pages"].values()))["imageinfo"][0]
    return image_info["thumburl"] if width else image_info["url"]
def clean_champion_name(champion_name):
    """清理英雄名稱，去除非字母字符"""
    return re.sub(r'[^a-zA-Z]', '', champion_name)

def game_results(request):
    site = EsportsClient("lol")
    tournaments = lp.get_tournaments('International', year=2024)
    if not tournaments:
        return render(request, 'game_results/game_results.html', {'matches': []})

    tournament = tournaments[3]
    tournament_name = tournament.name
    print(f"選定比賽：{tournament_name}")

    # 載入圖片快取
    image_cache_path = Path("player_images.json")
    if image_cache_path.exists():
        with open(image_cache_path, "r", encoding="utf-8") as f:
            player_image_cache = json.load(f)
    else:
        player_image_cache = {}

    # 初始化 Tab 分類字典（動態建立）
    tab_by_gameid = {}

    # 查詢所有比賽資料
    broad_query = site.cargo_client.query(
        tables="ScoreboardGames=SG, ScoreboardPlayers=SP, Players=P",
        join_on="SG.GameId=SP.GameId, SP.Link=P.OverviewPage",
        fields="SG.Team1, SG.Team2, SP.Champion, SP.Role, SP.Team, P.Player=Player, SG.Winner, SG.Gamename, SG.GameId, SG.OverviewPage",
        where=f'SG.Tournament="{tournament_name}"',
        order_by="SG.GameId ASC",
    )

    role_order = ["Top", "Jungle", "Mid", "Bot", "Support"]
    match_map = {}

    # 先查詢tab，並將tab加入 unique_tab 集合
    unique_tab = set()
    tab_query = site.cargo_client.query(
        tables="ScoreboardCounters=SC,ScoreboardGames=SG",
        join_on="SG.OverviewPage=SC.OverviewPage",
        fields="SC.Tab",
        where=f'SG.Tournament="{tournament_name}"',
    )

    for row in tab_query:
        unique_tab.add(row['Tab'])  # 直接將 Tab 加入 unique_tab 集合

    print(f"所有不同的 Tab: {unique_tab}")

    # 根據 GameId 設定 Tab
    for row in broad_query:
        game_id = row["GameId"]

        # 先搜尋對應的 Tab，若無則為 Unknown
        tab = 'Unknown'
        for t in unique_tab:
            if t in game_id:
                tab = t
                break

        # 若 Tab 不存在於字典中，創建一個新的 set
        if tab not in tab_by_gameid:
            tab_by_gameid[tab] = set()

        # 儲存到字典
        tab_by_gameid[tab].add(game_id)

        player_name = row["Player"]
        role = row["Role"]
        champion = clean_champion_name(row["Champion"])  # 清理英雄名稱
        team1 = row["Team1"]
        team2 = row["Team2"]
        player_team = row["Team"]
        overview = row["OverviewPage"]
        gamename = row["Gamename"]

        tournament_info = f'{overview.split("/")[0]} - {tab} {gamename}'
        print(f"Game ID: {game_id}, Tab: {tab}, OverviewPage: {overview}")

        # 抓圖片（快取）
        if player_name not in player_image_cache:
            print(f"抓取圖片：{player_name}")
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

        player_info = {
            "image": player_image_cache[player_name],
            "champion": f'/champion/{champion}.png',  # 使用本地圖片
            "role": role,
            "name": player_name
        }

        if game_id not in match_map:
            match_map[game_id] = {
                "Tournament": tournament_info,
                "Team1": team1,
                "Team2": team2,
                "Tab": tab,
                "Winner": row["Winner"],
                "Players1_by_role": {},
                "Players2_by_role": {}
            }

        match = match_map[game_id]

        if player_team == match["Team1"]:
            match["Players1_by_role"][role] = player_info
        elif player_team == match["Team2"]:
            match["Players2_by_role"][role] = player_info

    # 加入對戰組合識別鍵
    for match in match_map.values():
        teams = sorted([match["Team1"], match["Team2"]])
        match["MatchGroup"] = f"{teams[0]} vs {teams[1]}"

    # 排序：tab → 對戰組合 → Game 名稱
    matches = sorted(
        match_map.values(),
        key=lambda m: (
            m["Tab"],
            m["MatchGroup"],
            m["Tournament"]
        )
    )

    # 寫回圖片快取
    with open(image_cache_path, "w", encoding="utf-8") as f:
        json.dump(player_image_cache, f, ensure_ascii=False, indent=2)

    return render(request, 'game_results/game_results.html', {
        'matches': matches,
        'role_order': role_order
    })
