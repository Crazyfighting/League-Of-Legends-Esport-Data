from django.shortcuts import render
from mwrogue.esports_client import EsportsClient
import openpyxl
import datetime as dt
import urllib.request

def game_results(request):
    # 日期設定
    date = "2025-04-06"
    date = dt.datetime.strptime(date, "%Y-%m-%d").date()

    # 建立 Client
    site = EsportsClient("lol")

    # 執行查詢，將比賽名稱添加到查詢條件中
    response = site.cargo_client.query(
        tables="ScoreboardGames=SG, ScoreboardPlayers=SP, Players=P",
        join_on="SG.GameId=SP.GameId, SP.Link=P.OverviewPage",
        fields="SG.Tournament, SG.Team1, SG.Team2, SP.Champion, SP.Role, P.Player=Player, SG.Winner",
        where='SG._pageName="Data:2023 Mid-Season Invitational"'
    )

    # 數據處理
    game_data = []
    if response:
        for game in response:  # 獲取多場比賽的資料
            player = game['Player']
            s = EsportsClient("lol")
            r = s.cargo_client.query(
                limit=1,
                tables="PlayerImages=PI, Tournaments=T",
                fields="PI.FileName",
                join_on="PI.Tournament=T.OverviewPage",
                where=f'Link="{player}"',
                order_by="PI.SortDate DESC, T.DateStart DESC"
            )

            if r:
                url = r[0]['FileName']
                url = get_filename_url_to_open(s, url, player)
                game_data.append({
                    "Tournament": game["Tournament"],
                    "Team1": game["Team1"],
                    "Team2": game["Team2"],
                    "Champion": 'https://ddragon.leagueoflegends.com/cdn/15.4.1/img/champion/' + game["Champion"] + '.png',
                    "Role": game["Role"],
                    "Player": game["Player"],
                    "Winner": game["Winner"],
                    "PlayerImage": url  # 圖片的 URL
                })

    # 返回到模板並顯示
    return render(request, 'game_results/game_results.html', {'game_data': game_data})

def get_filename_url_to_open(site: EsportsClient, filename, player, width=None):
    response = site.client.api(
        action="query",
        format="json",
        titles=f"File:{filename}",
        prop="imageinfo",
        iiprop="url",
        iiurlwidth=width,
    )

    image_info = next(iter(response["query"]["pages"].values()))["imageinfo"][0]

    if width:
        url = image_info["thumburl"]
    else:
        url = image_info["url"]

    # 下載圖片到本地，並返回圖片路徑
    image_path = f"{player}.png"
    return url
