from football.match_finder import TeamMatch


def get_mock_fixtures():
    return [
        TeamMatch("M1", "Arsenal", "Chelsea", "Premier League", "2026-01-01T18:00:00Z"),
        TeamMatch("M2", "Barcelona", "Real Madrid", "La Liga", "2026-01-02T20:00:00Z"),
        TeamMatch("M3", "Liverpool", "Manchester City", "Premier League", "2026-01-03T19:00:00Z"),
    ]
