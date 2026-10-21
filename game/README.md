# 7:30

A short romance for a classroom projector. It is an introduction to decision making. Open `index.html` in any browser. No install, no build.

One person drives the mouse. Read the line out loud, let the room shout, then click. A full night is about 14 votes and runs 15–20 minutes. Keys 1, 2, and 3 pick the buttons. Space advances a line.

The name field prints on the last card.

You have one Friday evening and two people who want it. Ken is loud: a photo, a joke, a steak he named Sir Loin. Vera is quiet: four seconds of voice, one real conversation. Momo is already at a party, eating the crackers and giving bad advice. The clock runs from 6:40pm to 9:40pm. Under that clock, the loud thing tends to win.

## On screen the whole time

- **Clock.** A joke that costs minutes marks the clock.
- **Ken stamps.** He laughs, and the hour gets shorter.
- **Vera hearts.** She notices when you listen. One line about her face greys her portrait, and she will not leave with you.
- **Momo**, in the portrait row and in your ear. When you ask her what they meant, she is funny and wrong.

Nothing is labeled as the correct choice. The funny line is the middle button when three choices are up. A path dies by portrait, not by a failure popup. Grey means that person is gone. A flicker means both of them will compare your excuse later.

## The last card

The card is the decision, not a score. It shows what you did, where you ended, who is with you, and what you actually heard. Each thing you heard is marked true or noise.

| Card | What you did | What you heard | Where you ended | Who is with you |
| --- | --- | --- | --- | --- |
| With Vera | You listened | The one real conversation, true | In the cab with her | Vera |
| Two true things | You sorted the noise | He saved you a seat, and he was nervous | Ken's table, then alone | No one |
| The whole show | You took the loud parts | Six stories, four of them noise | Still at the loud table | No one |
| A nice dinner | You liked the surface | You never heard it | A polite goodbye | No one |
| Two taxis | You tried to keep both | You never heard it | Between them | No one |

The lesson is one line, and it appears only on that card. Time pressure makes a photo, a face, or a joke beat what the person actually said.

## If you edit the night

`story.json` is the script. Opening this folder as a file cannot fetch that JSON in Chrome, and a hanging fetch would freeze the page, so `index.html` also carries a copy. Served over http, the page uses `story.json`. Opened as a file, it uses the copy. After an edit, serve the folder if you want the file to win:

```bash
python3 -m http.server
```

Then open the `game/` URL. No packages.
