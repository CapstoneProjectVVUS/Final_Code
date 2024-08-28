from langchain.agents import Tool, load_tools
from langchain.tools import StructuredTool
from langchain.tools.retriever import create_retriever_tool

import bs4
import requests
from langchain_community.document_loaders import UnstructuredHTMLLoader
from datetime import date


def obtain_live_score():

    # response = open("./Data/prev.html", "r", encoding='utf-8').read()
    response = requests.get("https://www.fih.hockey/events/the-olympic-games-paris-2024/schedule-fixtures-results").content
    soup = bs4.BeautifulSoup(response, 'html.parser')

    output_list = []

    for fixture in soup.find_all(class_='fixtures-body'):
        for fixtures_group in fixture.find_all(class_='fixtures-group'):
            top_container = fixture.find(class_="fixtures-top")
            # print(top_container)
            # Find the mens fixture container or womens container
            gender_container = top_container.find(class_="fixtures-gender--mens")
            if gender_container == None:
                gender_container = top_container.find(class_="fixtures-gender--womens")
            #Extract the gender of the current matchup
            gender = gender_container.get_text().strip()
            # print(gender)
            # exit(0)
            for match in fixtures_group.find_all('li', class_='complete hand-cursor'):
                # print(match)
        # Extract team names
                teams = match.find_all('p', class_='team-name')
                teams_list = []
                for team in teams:
                    team.get_text(strip=True)
                    teams_list.append(team.get_text().strip())

                # print(teams_list)
                team_a, team_b = teams_list[0], teams_list[1]
                scores = match.find_all('p', class_='score')
                scores_list = []
                for score in scores:
                    scores_list.append(score.get_text().strip())
                # print(scores_list)
                score_a, score_b = scores_list[0], scores_list[1]

                # Extract match time
                match_time = match.find('div', class_='team-time').find('div', class_='timer-counter').get_text(strip=True)
                match_time = match_time[:-1] + " minutes"
                # print(match_time)

                # Extract venue
                medal_div = match.find('div', class_='fixtures-venue')
                if medal_div:
                    venue = medal_div.find('p', class_='venue').get_text(strip=True)
                    sentence = f"Paris Summer Olympics 2024 {gender}: {team_a} (score: {score_a}) vs {team_b} (score: {score_b}) in the {venue} match."

                else:
                    sentence = f"Paris Summer Olympics 2024 {gender}: {team_a} (score: {score_a}) vs {team_b} (score: {score_b})."

                output_list.append(sentence)
            # Print the sentence
                # print(sentence)
    return output_list


# #Usage with preloaded html file:
# #Example usage:
# print(obtain_live_score())
# print(len(obtain_live_score()))

# def obtain_live_score():

#     response = open("./Data/prev.html", "r", encoding='utf-8').read()

#     soup = bs4.BeautifulSoup(response, 'html.parser')
#     output_list = []
#     # Iterate over all 'fixtures-listing-bottom' divs
#     for listing in soup.find_all('div', class_='fixtures-listing-bottom'):
#         # Extract the fixture title
#         title_div = listing.find('div', class_='fixtures-head')
#         if title_div:
#             title = title_div.find('h4', class_='fixtures-title').get_text(strip=True)
#         # Iterate over each fixture group
#         for fixture in listing.find_all(class_='fixtures-body'):
#             for fixtures_group in fixture.find_all(class_='fixtures-group'):

#                 top_container = fixture.find(class_="fixtures-top")
#                 # Find the mens fixture container or womens container
#                 gender_container = top_container.find(class_="fixtures-gender--mens")
#                 if gender_container == None:
#                     womens_container = top_container.find(class_="fixtures-gender--womens")
#                 #Extract the gender of the current matchup
#                 gender = gender_container.get_text().strip()
#                 # print(gender)
#                 # exit(0)
#                 for match in fixtures_group.find_all('li', class_='live hand-cursor'):
#                     # print(match)
#             # Extract team names
#                     teams = match.find_all('p', class_='team-name')
#                     teams_list = []
#                     for team in teams:
#                         team.get_text(strip=True)
#                         teams_list.append(team.get_text().strip())

#                     # print(teams_list)
#                     team_a, team_b = teams_list[0], teams_list[1]
#                     # exit(0)
#                     # team_b = match.find('div', class_='team team-b').find('p', class_='team-name').get_text(strip=True)
#                     # Extract scores
#                     scores = match.find_all('p', class_='score')
#                     scores_list = []
#                     for score in scores:
#                         scores_list.append(score.get_text().strip())
#                     # print(scores_list)
#                     score_a, score_b = scores_list[0], scores_list[1]

#                     # Extract match time
#                     match_time = match.find('div', class_='team-time').find('div', class_='timer-counter').get_text(strip=True)
#                     match_time = match_time[:-1] + " minutes"
#                     # print(match_time)

#                     # Extract venue
#                     # venue_div = match.find('div', class_='fixtures-venue')
#                     # if venue_div:
#                     #     venue = venue_div.find('p', class_='venue').get_text(strip=True)
#                     # else:
#                     #     venue = 'Unknown Venue'
#                     # print(venue)
#                     # Generate the sentence of information
#                     sentence = f"{title}: {team_a} (score: {score_a}) vs {team_b} (score: {score_b}) at {match_time}."
#                     output_list.append(sentence)
#                 # Print the sentence
#                     # print(sentence)
#     return sentence
