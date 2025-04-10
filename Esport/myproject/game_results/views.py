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

    # 先查詢特定頁面底下的比賽 RiotPlatformGameId
    page_to_query = "Data:2023 Mid-Season Invitational"
    game_id_response = site.cargo_client.query(
        tables="MatchScheduleGame=MSG,MatchSchedule=MS",
        fields="MSG.RiotPlatformGameId",
        where='MSG._pageName="%s" AND MSG.RiotPlatformGameId IS NOT NULL' % page_to_query,
        join_on="MSG.MatchId=MS.MatchId",
        order_by="MS.N_Page, MS.N_MatchInPage, MSG.N_GameInMatch",
        limit=20
    )

    riot_game_ids = [f'"{g["RiotPlatformGameId"]}"' for g in game_id_response]
    if not riot_game_ids:
        return render(request, 'game_results/game_results.html', {'game_data': []})

    game_id_filter = f"SG.RiotPlatformGameId IN ({','.join(riot_game_ids)})"

    # 查詢對應的比賽資料
    response = site.cargo_client.query(
        tables="ScoreboardGames=SG, ScoreboardPlayers=SP, Players=P",
        join_on="SG.GameId=SP.GameId, SP.Link=P.OverviewPage",
        fields="SG.Tournament, SG.Team1, SG.Team2, SP.Champion, SP.Role, P.Player=Player, SG.Winner",
        where=f"{game_id_filter} AND SG.DateTime_UTC >= '{date} 00:00:00' AND SG.DateTime_UTC <= '{date + dt.timedelta(days=1)} 00:00:00'"
    )

    # 數據處理
    game_data = []
    if response:
        for game in response:
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
                    "Champion": f'https://ddragon.leagueoflegends.com/cdn/15.4.1/img/champion/{game["Champion"]}.png',
                    "Role": game["Role"],
                    "Player": game["Player"],
                    "Winner": game["Winner"],
                    "PlayerImage": url
                })

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
