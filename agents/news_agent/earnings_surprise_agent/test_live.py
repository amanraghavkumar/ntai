from surprise import classify_surprise


def test() -> None:
    assert classify_surprise("Infosys beats estimates, profit up 8%")[0] == "beat"
    assert classify_surprise("Wipro misses estimates on weak deal wins")[0] == "miss"
    assert classify_surprise("TCS profit in line with estimates")[0] == "inline"
    assert classify_surprise("HDFC Bank quarterly results today")[0] == "results_only"
    assert classify_surprise("RBI keeps repo rate unchanged")[0] is None
    print("OK surprise tags")


if __name__ == "__main__":
    test()
    print("ALL EARNINGS TESTS PASSED")
