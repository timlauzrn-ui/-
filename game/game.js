(function () {
  "use strict";

  function parseClock(text) {
    var match = /^(\d{1,2}):(\d{2})\s*(am|pm)$/i.exec(String(text).trim());
    if (!match) throw new Error("Bad clock: " + text);
    var hour = parseInt(match[1], 10);
    var minute = parseInt(match[2], 10);
    var ap = match[3].toLowerCase();
    if (ap === "pm" && hour !== 12) hour += 12;
    if (ap === "am" && hour === 12) hour = 0;
    return hour * 60 + minute;
  }

  function formatClock(total) {
    total = ((total % 1440) + 1440) % 1440;
    var hour = Math.floor(total / 60);
    var minute = total % 60;
    var ap = hour >= 12 ? "pm" : "am";
    hour = hour % 12;
    if (hour === 0) hour = 12;
    return hour + ":" + (minute < 10 ? "0" : "") + minute + ap;
  }

  function flag(state, key) {
    var value = state.flags[key];
    return value === undefined ? false : value;
  }

  function matches(cond, state) {
    if (!cond) return true;
    if (cond.heartsAtLeast != null && state.hearts < cond.heartsAtLeast) return false;
    if (cond.clockBefore && state.clock >= parseClock(cond.clockBefore)) return false;
    var key;
    if (cond.not) {
      for (key in cond.not) {
        if (Object.prototype.hasOwnProperty.call(cond.not, key) && flag(state, key) === cond.not[key]) return false;
      }
    }
    for (key in cond) {
      if (!Object.prototype.hasOwnProperty.call(cond, key)) continue;
      if (key === "heartsAtLeast" || key === "clockBefore" || key === "not") continue;
      if (flag(state, key) !== cond[key]) return false;
    }
    return true;
  }

  function fill(text, state) {
    var love = "them";
    if (state.flags.loveTarget === "ken") love = "Ken";
    if (state.flags.loveTarget === "vera") love = "Vera";
    return String(text)
      .split("{player}").join(state.playerName || "Your name")
      .split("{stoodName}").join(state.flags.stoodName || "them")
      .split("{loveName}").join(love);
  }

  function applyFx(state, fx) {
    if (!fx) return;
    var key;
    if (fx.set) {
      for (key in fx.set) {
        if (Object.prototype.hasOwnProperty.call(fx.set, key)) state.flags[key] = fx.set[key];
      }
    }
    if (fx.addHearts) state.hearts += fx.addHearts;
    if (fx.addStamps) state.stamps += fx.addStamps;
    if (fx.addMinutes) state.clock += fx.addMinutes;
    if (fx.grey) fx.grey.forEach(function (id) { state.grey[id] = true; });
    if (fx.flicker) fx.flicker.forEach(function (id) { state.flicker[id] = true; });
    if (state.flags.veraGrey) state.grey.vera = true;
    if (state.flags.notesCompared) {
      state.flicker.ken = true;
      state.flicker.vera = true;
    }
  }

  function prepStandup(state) {
    var flags = state.flags;
    if (flags.table === "ken") {
      flags.stoodName = "Vera";
      flags.loveTarget = "vera";
    } else if (flags.table === "vera") {
      flags.stoodName = "Ken";
      flags.loveTarget = "ken";
    } else {
      flags.stoodName = "both of them";
      flags.loveTarget = flags.opened === "vera" ? "ken" : "vera";
    }
    return null;
  }

  function readOpened(state) {
    var flags = state.flags;
    flags.readOne = true;
    if (flags.opened === "vera") {
      flags.readVera = true;
      return "truth-vera";
    }
    if (flags.opened === "ken") {
      flags.readKen = true;
      return "truth-ken";
    }
    flags.readKen = true;
    flags.readLoud = true;
    return "truth-loud";
  }

  function resolveEnding(state) {
    var flags = state.flags;
    if (flags.plusOne && flags.heardPlan && !flags.veraGrey && !flags.looksFirst && !flags.notesCompared && !flags.doubleBooked) {
      return "plus-one";
    }
    if (flags.doubleBooked) return "two-taxis";
    if (flags.armful && !flags.sorted) return "armful";
    if (flags.sorted) return "two-real";
    if (flags.opened === "vera" && !flags.heardPlan && !flags.readBoth) return "nice";
    return "nice";
  }

  function loadout(story, state) {
    var card = story.endings[state.endingId];
    return {
      ending: state.endingId,
      title: card.title,
      player: state.playerName || "Your name",
      whatYouDid: card.attention,
      heard: card.heard,
      where: card.where,
      withYou: card.withYou === "________" ? "" : card.withYou,
      veraHere: !!card.veraPresent,
      kenStamps: state.stamps,
      veraHearts: state.hearts
    };
  }

  function createGame(story) {
    var state;

    function blank() {
      return {
        playerName: "Your name",
        hearts: 0,
        stamps: 0,
        clock: parseClock("6:40pm"),
        votes: 0,
        flags: {},
        grey: { momo: false, ken: false, vera: false },
        flicker: { momo: false, ken: false, vera: false },
        sceneId: null,
        line: 0,
        phase: "lines",
        endingId: null,
        minuteBump: 0
      };
    }

    function scene() {
      return story.scenes[state.sceneId];
    }

    function visible(list) {
      return (list || []).filter(function (choice) {
        return matches(choice.require, state);
      });
    }

    function ordered(list) {
      var joke = null;
      var rest = [];
      list.forEach(function (choice) {
        if (choice.joke && !joke) joke = choice;
        else rest.push(choice);
      });
      var placed;
      if (joke && rest.length >= 2) placed = [rest[0], joke, rest[1]].concat(rest.slice(2));
      else if (joke && rest.length === 1) placed = [rest[0], joke];
      else if (joke) placed = [joke];
      else placed = rest.slice();
      return placed.map(function (choice, index) {
        var slot = index;
        if (joke && choice === joke) slot = 1;
        else if (joke && rest.length >= 2) slot = choice === rest[0] ? 0 : 2;
        else if (joke && rest.length === 1) slot = 0;
        return { choice: choice, slot: slot };
      });
    }

    function go(id, hops) {
      if (hops == null) hops = 0;
      if (hops > 40) throw new Error("Scene loop at " + id);
      var nextScene = story.scenes[id];
      if (!nextScene) throw new Error("Missing scene " + id);
      if (nextScene.clock) {
        var at = parseClock(nextScene.clock);
        if (at > state.clock) state.clock = at;
      }
      if (nextScene.addMinutes) state.clock += nextScene.addMinutes;
      applyFx(state, nextScene.fx);
      if (nextScene.op === "prepStandup") {
        var dest = prepStandup(state);
        if (dest) return go(dest, hops + 1);
      }
      if (nextScene.route) {
        var rule = null;
        var i;
        for (i = 0; i < nextScene.route.length; i++) {
          if (matches(nextScene.route[i].if, state)) {
            rule = nextScene.route[i];
            break;
          }
        }
        if (!rule) throw new Error("No route from " + id);
        applyFx(state, rule.fx);
        return go(rule.to, hops + 1);
      }
      if (nextScene.ending) {
        state.sceneId = id;
        state.endingId = resolveEnding(state);
        state.phase = "ending";
        state.line = 0;
        return;
      }
      state.sceneId = id;
      state.line = 0;
      if (nextScene.lines && nextScene.lines.length) {
        state.phase = "lines";
        return;
      }
      if (nextScene.choices && visible(nextScene.choices).length) {
        state.phase = "choice";
        return;
      }
      if (nextScene.next) return go(nextScene.next, hops + 1);
      throw new Error("Stuck in " + id);
    }

    function start(name) {
      var keep = name || (state && state.playerName) || "Your name";
      state = blank();
      state.playerName = keep;
      go(story.start);
    }

    function advance() {
      if (state.phase !== "lines") return false;
      state.minuteBump = 0;
      var current = scene();
      state.line += 1;
      if (state.line < current.lines.length) return true;
      if (visible(current.choices).length) {
        state.phase = "choice";
        return true;
      }
      if (current.next) {
        go(current.next);
        return true;
      }
      throw new Error("No exit from " + state.sceneId);
    }

    function choose(index) {
      if (state.phase !== "choice") return false;
      var options = ordered(visible(scene().choices));
      var picked = options[index];
      if (!picked) return false;
      var choice = picked.choice;
      state.votes += 1;
      state.minuteBump = (choice.fx && choice.fx.addMinutes) || 0;
      applyFx(state, choice.fx);
      var lands = choice.to === "end" || choice.to === "period";
      if ((!choice.fx || !choice.fx.addMinutes) && !lands) state.clock += 3;
      if (choice.op === "readOpened") {
        go(readOpened(state));
        return true;
      }
      if (!choice.to) throw new Error("Choice has no destination in " + state.sceneId);
      go(choice.to);
      return true;
    }

    function view() {
      var base = {
        clock: formatClock(state.clock),
        hearts: state.hearts,
        stamps: state.stamps,
        votes: state.votes,
        grey: { momo: state.grey.momo, ken: state.grey.ken, vera: state.grey.vera },
        flicker: { momo: state.flicker.momo, ken: state.flicker.ken, vera: state.flicker.vera },
        minuteBump: state.minuteBump,
        playerName: state.playerName
      };
      if (state.phase === "ending") {
        base.phase = "ending";
        base.endingId = state.endingId;
        base.card = story.endings[state.endingId];
        base.research = story.research;
        base.loadout = loadout(story, state);
        return base;
      }
      var current = scene();
      base.sceneId = state.sceneId;
      base.phase = state.phase;
      if (state.phase === "lines") {
        var line = current.lines[state.line];
        base.speaker = line.speaker;
        base.text = fill(line.text, state);
        return base;
      }
      var last = current.lines && current.lines.length ? current.lines[current.lines.length - 1] : null;
      if (last) {
        base.speaker = last.speaker;
        base.text = fill(last.text, state);
      }
      base.choices = ordered(visible(current.choices)).map(function (item) {
        return { text: fill(item.choice.text, state), joke: !!item.choice.joke, slot: item.slot };
      });
      return base;
    }

    function setName(name) {
      state.playerName = name || "Your name";
    }

    state = blank();
    return { start: start, advance: advance, choose: choose, view: view, setName: setName };
  }

  function loadStoryFromPage() {
    function inline() {
      var el = document.getElementById("story-data");
      if (!el || !el.textContent.trim()) throw new Error("The episode text is missing.");
      return JSON.parse(el.textContent);
    }
    try {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", "story.json", false);
      xhr.send(null);
      if (xhr.responseText && xhr.responseText.trim().charAt(0) === "{") return JSON.parse(xhr.responseText);
    } catch (err) {
      return inline();
    }
    return inline();
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"]/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch];
    });
  }

  function boot() {
    var story = loadStoryFromPage();
    var game = createGame(story);
    var speakerEl = document.getElementById("speaker");
    var lineEl = document.getElementById("line");
    var nextBtn = document.getElementById("next");
    var choicesEl = document.getElementById("choices");
    var endingEl = document.getElementById("ending");
    var stage = document.getElementById("stage");
    var clockEl = document.getElementById("clock");
    var stampsEl = document.getElementById("stamps");
    var heartsEl = document.getElementById("hearts");
    var voteEl = document.getElementById("vote-count");
    var nameEl = document.getElementById("player-name");
    var portraits = {
      momo: document.querySelector('[data-who="momo"]'),
      ken: document.querySelector('[data-who="ken"]'),
      vera: document.querySelector('[data-who="vera"]')
    };
    var names = { momo: "Momo", ken: "Ken", vera: "Vera", you: "You", email: "Mail", host: "Host", driver: "Driver" };

    function paint() {
      var snapshot = game.view();
      clockEl.textContent = snapshot.clock;
      stampsEl.textContent = "Ken stamps " + snapshot.stamps;
      heartsEl.textContent = "Vera hearts " + snapshot.hearts;
      clockEl.classList.toggle("bump", !!snapshot.minuteBump);
      if (snapshot.minuteBump) clockEl.setAttribute("data-bump", "+" + snapshot.minuteBump + " min");
      else clockEl.removeAttribute("data-bump");
      ["momo", "ken", "vera"].forEach(function (id) {
        portraits[id].classList.toggle("grey", !!snapshot.grey[id]);
        portraits[id].classList.toggle("flicker", !!snapshot.flicker[id] && !snapshot.grey[id]);
        portraits[id].classList.toggle("talking", snapshot.phase !== "ending" && snapshot.speaker === id);
      });
      if (snapshot.phase === "ending") {
        stage.hidden = true;
        choicesEl.hidden = true;
        endingEl.hidden = false;
        voteEl.textContent = snapshot.votes + " votes";
        renderCard(snapshot);
        return;
      }
      endingEl.hidden = true;
      stage.hidden = false;
      stage.setAttribute("data-scene", snapshot.sceneId);
      speakerEl.textContent = names[snapshot.speaker] || snapshot.speaker || "";
      speakerEl.setAttribute("data-speaker", snapshot.speaker || "");
      lineEl.textContent = snapshot.text || "";
      if (snapshot.phase === "lines") {
        choicesEl.hidden = true;
        nextBtn.hidden = false;
        voteEl.textContent = "Next vote " + (snapshot.votes + 1);
        return;
      }
      nextBtn.hidden = true;
      choicesEl.hidden = false;
      choicesEl.innerHTML = "";
      voteEl.textContent = "Vote " + (snapshot.votes + 1);
      snapshot.choices.forEach(function (choice, index) {
        var button = document.createElement("button");
        button.type = "button";
        button.className = "choice";
        button.style.gridColumn = String(choice.slot + 1);
        button.textContent = choice.text;
        button.addEventListener("click", function () {
          game.choose(index);
          paint();
        });
        choicesEl.appendChild(button);
      });
    }

    function renderCard(snapshot) {
      var card = snapshot.card;
      var heard = card.heard.length
        ? card.heard.map(function (item) {
          var label = item.quality === "real" ? "True" : "Noise";
          return "<li><span class=\"quality " + item.quality + "\">" + label + "</span> " + escapeHtml(item.name) + "</li>";
        }).join("")
        : "<li class=\"none\">You never heard it.</li>";
      var basket = snapshot.endingId === "two-taxis" ? "<p class=\"basket\">The basket is empty.</p>" : "";
      endingEl.innerHTML =
        "<article class=\"invite\">" +
        "<p class=\"kicker\">The decision</p>" +
        "<h2>" + escapeHtml(card.title) + "</h2>" +
        "<p class=\"who\">" + escapeHtml(snapshot.playerName) + "</p>" +
        "<dl>" +
        "<div><dt>What you did</dt><dd>" + escapeHtml(card.attention) + "</dd></div>" +
        "<div><dt>Where you ended</dt><dd>" + escapeHtml(card.where) + "</dd></div>" +
        "<div><dt>Who is with you</dt><dd>" + escapeHtml(card.withYou) + "</dd></div>" +
        "</dl>" +
        "<h3>What you heard</h3><ul class=\"plans\">" + heard + "</ul>" +
        "<p class=\"phone\"><span>Momo</span> " + escapeHtml(card.momo) + "</p>" +
        basket +
        "<p class=\"research\">" + escapeHtml(snapshot.research) + "</p>" +
        "<button type=\"button\" id=\"again\">Play again</button>" +
        "</article>";
      document.getElementById("again").addEventListener("click", function () {
        game.start(nameEl.value.trim());
        paint();
      });
    }

    nextBtn.addEventListener("click", function () {
      game.advance();
      paint();
    });
    stage.addEventListener("click", function (event) {
      if (event.target.closest && event.target.closest("button")) return;
      if (game.view().phase === "lines") {
        game.advance();
        paint();
      }
    });
    nameEl.addEventListener("input", function () {
      game.setName(nameEl.value.trim());
      if (game.view().phase === "ending") paint();
    });
    document.addEventListener("keydown", function (event) {
      if (event.target && event.target.matches && event.target.matches("input, textarea")) return;
      var snapshot = game.view();
      if ((event.key === " " || event.key === "Enter") && snapshot.phase === "lines") {
        event.preventDefault();
        game.advance();
        paint();
      }
      if ((event.key === "1" || event.key === "2" || event.key === "3") && snapshot.phase === "choice") {
        game.choose(Number(event.key) - 1);
        paint();
      }
    });

    game.start(nameEl.value.trim());
    paint();
  }

  globalThis.DinnerGame = { createGame: createGame, parseClock: parseClock, formatClock: formatClock };

  if (typeof document !== "undefined" && document.getElementById("stage")) {
    try {
      boot();
    } catch (err) {
      var failure = document.createElement("p");
      failure.className = "boot-error";
      failure.textContent = "This episode did not start. " + err.message;
      document.body.appendChild(failure);
    }
  }
})();
