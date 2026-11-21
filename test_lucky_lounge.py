
import pytest
import lucky_lounge
from lucky_lounge import GamblingApp


# Simple fake GUI objects so tests do not need to open a window.

class FakeEntry:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeLabel:
    def config(self, **kwargs):
        pass


class FakeButton:
    def config(self, **kwargs):
        pass


# -----------------------------------------
# TC-01: Test money_amount()
# -----------------------------------------

def test_TC01_validate_bet(monkeypatch):
    # Create an application object without opening the GUI.
    app = GamblingApp.__new__(GamblingApp)
    app.money = 1000.0

    errors = []

    monkeypatch.setattr(
        lucky_lounge.messagebox,
        "showerror",
        lambda title, message: errors.append(message)
    )

    # Valid bet: $50
    assert app.money_amount(FakeEntry("50")) == 50.0

    # Valid bet: entire balance
    assert app.money_amount(FakeEntry("1000")) == 1000.0

    # Invalid bets
    invalid_inputs = [
        "0",
        "-5",
        "1001",
        "letters",
        "999999999"
    ]

    for value in invalid_inputs:
        assert app.money_amount(FakeEntry(value)) is None

    # Each invalid bet should produce an error message.
    assert len(errors) == len(invalid_inputs)


# -----------------------------------------
# TC-02: Test picture game payout
# -----------------------------------------

def test_TC02_calculate_picture_payout(monkeypatch):

    def run_picture_test(symbols, expected_payout):
        app = GamblingApp.__new__(GamblingApp)

        # The bet was already deducted in pull_lever().
        app.money = 990.0
        app.spin_count = 15

        app.picture_symbols = ["🍒", "🍋", "🔔", "⭐", "7️⃣"]
        app.slot_labels = [
            FakeLabel(),
            FakeLabel(),
            FakeLabel()
        ]

        app.lever_button = FakeButton()
        app.picture_result = FakeLabel()

        # Prevent GUI updates.
        app.update_money = lambda: None

        # Make the random symbols predictable.
        results = iter(symbols)
        monkeypatch.setattr(
            lucky_lounge.random,
            "choice",
            lambda choices: next(results)
        )

        # Run the original picture payout logic.
        app.spin_animation(10)

        assert app.money == 990.0 + expected_payout

    # Three different symbols: $0 payout
    run_picture_test(
        ["🍒", "🍋", "⭐"],
        0
    )

    # Two matching symbols: $20 payout
    run_picture_test(
        ["🍒", "🍒", "⭐"],
        20
    )

    # Three matching symbols: $80 payout
    run_picture_test(
        ["7️⃣", "7️⃣", "7️⃣"],
        80
    )


# -----------------------------------------
# TC-03: Test save_game() and load_game()
# -----------------------------------------

def test_TC03_save_and_load_balance(tmp_path, monkeypatch):

    app = GamblingApp.__new__(GamblingApp)
    app.money = 725.50

    # Prevent GUI updates.
    app.update_money = lambda: None

    messages = {
        "success": [],
        "errors": []
    }

    monkeypatch.setattr(
        lucky_lounge.messagebox,
        "showinfo",
        lambda title, message: messages["success"].append(message)
    )

    monkeypatch.setattr(
        lucky_lounge.messagebox,
        "showerror",
        lambda title, message: messages["errors"].append(message)
    )

    save_file = tmp_path / "player_save.txt"

    # Save a positive balance.
    monkeypatch.setattr(
        lucky_lounge.filedialog,
        "asksaveasfilename",
        lambda **kwargs: str(save_file)
    )

    app.save_game()

    assert save_file.exists()
    assert save_file.read_text().strip() == "725.50"

    # Load the saved balance.
    app.money = 0.0

    monkeypatch.setattr(
        lucky_lounge.filedialog,
        "askopenfilename",
        lambda **kwargs: str(save_file)
    )

    app.load_game()

    assert app.money == 725.50

    # Save and load a zero balance.
    app.money = 0.0
    app.save_game()

    app.money = 500.0
    app.load_game()

    assert app.money == 0.0

    # Negative balance in the save file should be rejected.
    save_file.write_text("-50.00")

    previous_balance = app.money
    app.load_game()

    assert app.money == previous_balance
    assert len(messages["errors"]) == 1

    # Invalid text in the save file should be rejected.
    save_file.write_text("not a number")

    app.load_game()

    assert app.money == previous_balance
    assert len(messages["errors"]) == 2

    # Missing file should produce an error.
    missing_file = tmp_path / "missing.txt"

    monkeypatch.setattr(
        lucky_lounge.filedialog,
        "askopenfilename",
        lambda **kwargs: str(missing_file)
    )

    app.load_game()

    assert app.money == previous_balance
    assert len(messages["errors"]) == 3
