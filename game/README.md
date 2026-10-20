# 7:30

A classroom episode for a projector. Open `index.html` in a browser. No install, no build.

One person drives the mouse. Read the line out loud, let the room shout, then click. A full night is about 14 votes and runs 15–20 minutes. Keys 1, 2, and 3 pick the buttons. Space advances a line.

The pencil field is the section's name. It prints on the bidding card.

## On screen the whole time

- **Clock**, from 6:40pm toward 9:40pm. A joke that costs minutes marks the clock.
- **Ken stamps.** Deal-favor. The loud commercial jokes earn them.
- **Vera hearts.** Attention. One careless line greys her portrait, and the plus-one dies with it.
- **Momo**, in the portrait row and in your ear. She is already at table 9 with the prawn crackers. When you ask her what to do, she is funny and wrong.

Nothing is labeled as the correct choice. The funny line is the middle button when three choices are up. A path dies by portrait, not by a failure popup. Grey means that person is out. A flicker means both directors will compare notes later.

## The card

The last screen is the invitation for the bidding game. That game is not in this episode. It can read the card:

- Capital
- Plans, each marked real or junk
- Seat
- Guest, or a blank line
- Whether Vera is in the room

| Card | Capital | Plans | Seat | Guest | Vera there |
| --- | --- | --- | --- | --- | --- |
| Plus-one | High | Her one page, real | Plus-one with Vera | Vera | Yes. She may speak once. She was in the room when the page was read. |
| Two real deals | Medium | Cold-storage lease and night-ferry catering, both real | Ken's solo sponsor | Blank | No |
| Armful of paper | A big number | Six plans, four of them junk | Ken's solo sponsor | Blank | No |
| Nice dinner | Low | No plan | Polite solo seat | Blank | No |
| Two taxis | Pocket change | No plan | Staff ticket | Blank | No |

The same fields are printed as JSON on the card under the research line. The research line appears only there: time pressure makes the loud thing (a steak photo, a face, a joke) beat the page you did not read.

## If you edit the night

`story.json` is the script. Opening this folder as a file cannot fetch that JSON in Chrome, and a hanging fetch would freeze the page, so `index.html` also carries a copy. Served over http, the page uses `story.json`. Opened as a file, it uses the copy. After an edit, serve the folder if you want the file to win:

```bash
python3 -m http.server
```

Then open the `game/` URL. No packages.
