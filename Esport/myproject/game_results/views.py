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

    # 先查詢特定頁面底下的比賽 RiotPlatformGameId 和 DateTime_UTC
    page_to_query = "Data:2023 Mid-Season Invitational"
    game_id_response = site.cargo_client.query(
        tables="MatchScheduleGame=MSG,MatchSchedule=MS",
        fields="MSG.RiotPlatformGameId, MS.DateTime_UTC",
        where='MSG._pageName="%s" AND MSG.RiotPlatformGameId IS NOT NULL' % page_to_query,
        join_on="MSG.MatchId=MS.MatchId",
        order_by="MS.N_Page, MS.N_MatchInPage, MSG.N_GameInMatch",
        limit=20
    )

    # 若沒有查詢到比賽，返回空資料
    if not game_id_response:
        return render(request, 'game_results/game_results.html', {'game_data': []})

    game_data = []

    # 處理每場比賽
    for game in game_id_response:
        # 取得比賽的 RiotPlatformGameId 和 DateTime_UTC
        game_id = game['RiotPlatformGameId']
        game_datetime = game['DateTime_UTC']
        print(f"Game Date and Time: {game_datetime}")

        # 查詢對應的比賽資料，這裡用 game_datetime 替代了原來的 date
        game_result_response = site.cargo_client.query(
            tables="ScoreboardGames=SG, ScoreboardPlayers=SP, Players=P",
            join_on="SG.GameId=SP.GameId, SP.Link=P.OverviewPage",
            fields="SG.Tournament, SG.Team1, SG.Team2, SP.Champion, SP.Role, P.Player=Player, SG.Winner, SG.DateTime_UTC",
            where=f"SG.RiotPlatformGameId='{game_id}' AND SG.DateTime_UTC='{game_datetime}'"
        )

        # 處理比賽結果
        if game_result_response:
            for result in game_result_response:
                # 查詢選手圖片
                player = result['Player']
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
                        "Tournament": result["Tournament"],
                        "Team1": result["Team1"],
                        "Team2": result["Team2"],
                        "Champion": f'https://ddragon.leagueoflegends.com/cdn/15.4.1/img/champion/{result["Champion"]}.png',
                        "Role": result["Role"],
                        "Player": result["Player"],
                        "Winner": result["Winner"],
                        "PlayerImage": url
                    })

    # 返回結果到模板
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

    return image_info["thumburl"] if width else image_info["url"]
