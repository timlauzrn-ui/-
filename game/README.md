# 7:30

A short, classroom-safe romance for a projector. The class plays a male lead. Three heroines stay on screen the whole evening. Open `index.html` in any browser. No install, no build.

One person drives the mouse. Read the line out loud, let the room shout, then click. A full night is about 14 votes and runs 15–20 minutes. Keys 1, 2, and 3 pick the buttons. Space advances a line. The name field prints on the invitation.

It is one Friday, 6:40pm to 9:40pm. You can actually show up for one person.

## Who is on screen

- **Momo**, childhood friend. She is already out, live-texting, usually wrong, and she is also a route.
- **Rin**, loud. She sends the photo and the joke. Laughs cost minutes. You win her by hearing the two true things under the bit: she saved you a seat, and she is nervous.
- **Vera**, quiet. Four-second voice note: one real conversation, don't perform. One line about her face greys her portrait and kills that route.

The chips are the clock and three affection counts: Momo, Rin, and Vera. Nothing is labeled as the correct choice. The funny line is the middle button when three choices are up. A path dies by portrait, not by a popup. Grey means that girl is gone. A flicker means Rin and Vera will compare your excuse later, and both of those routes die.

## The three routes

You open one thread, or you tell all three you are on the way. That reply books every taxi and leaves the guest line blank.

You listen to both, only to the one you opened, or you ask Momo. She will be funny and wrong.

At 7:30 you sit with Rin, with Vera, or at French toast. Toast is a real scene only if you listened. Otherwise you eat alone, and Momo can still be asked to sit down.

The text to the person you stand up is honest, a fake excuse, or an autocorrect "I love you" to the wrong girl. Vera survives that only if her affection is already high.

On the date, ask what she meant, tell a joke, or comment on her face. The face line greys her. At 9:10 you have one line. She says yes only if you listened, you asked, and her portrait is still lit.

## The last card

Every path ends on the same invitation, including the misses. The plot never explains the card. The only thing that changes is the guest line.

- **Vera, Rin, or Momo** — that route was won.
- **Blank** — you told everyone you were coming, you took the whole show and never heard her, or you liked the face and the voice and never asked.

Momo texts one line under the card. Under that, one sentence: time pressure makes the photo, the face, or the joke beat what she said. The next game starts from this invitation.

## If you edit the night

`story.json` is the script. Opening this folder as a file cannot fetch that JSON in Chrome, and a hanging fetch would freeze the page, so `index.html` also carries a copy. Served over http, the page uses `story.json`. Opened as a file, it uses the copy. After an edit, serve the folder if you want the file to win:

```bash
python3 -m http.server
```

Then open the `game/` URL. No packages.
