// Climbing wall mini-game: click the holds in order (lowest first) to move the
// climber up the wall. After the top hold, click the sun to reach it and
// celebrate. A "Climb again" button appears afterwards to start over.
//
// Each move to the next hold has a random chance of falling back to the bottom.
// The per-hold risks are re-rolled for every climb, and are split so that the
// overall chance of falling somewhere on the way up is TOTAL_FALL_CHANCE.

// Climbing videos play at 1.25x speed by default (viewers can still change it
// from the video's own menu).
const VIDEO_SPEED = 1.25;

document.addEventListener("DOMContentLoaded", () => {
    const videos = Array.from(document.querySelectorAll(".climb-section video"));

    videos.forEach((video) => {
        const setSpeed = () => {
            video.defaultPlaybackRate = VIDEO_SPEED;
            video.playbackRate = VIDEO_SPEED;
        };
        setSpeed();
        // Some browsers reset the speed once the video loads, so set it again then.
        video.addEventListener("loadedmetadata", setSpeed);

        // Only one video plays at a time: starting one pauses all the others.
        video.addEventListener("play", () => {
            videos.forEach((other) => {
                if (other !== video && !other.paused) other.pause();
            });
        });
    });
});

document.addEventListener("DOMContentLoaded", () => {
    const wall = document.querySelector(".climbing-wall");
    const climber = document.getElementById("climber");
    const treasure = document.getElementById("treasure");
    if (!wall || !climber) return;

    const holds = Array.from(wall.querySelectorAll(".hold"))
        .sort((a, b) => Number(a.dataset.level) - Number(b.dataset.level));
    const lastLevel = holds.length;

    const holdColor = "#cf7a4c"; // matches .hold in style.css
    const reachedColor = "#4f7edc"; // sky blue from the Zion banner photo

    const TOTAL_FALL_CHANCE = 0.7;
    let fallRisks = [];

    // Randomly split the overall fall chance across the holds.
    // A full climb succeeds only if every move succeeds, so the per-hold
    // success chances must multiply to (1 - TOTAL_FALL_CHANCE). Each hold gets
    // a random share of that: success_i = 0.3 ^ (weight_i / sum of weights).
    function rollFallRisks() {
        const weights = holds.map(() => 0.2 + Math.random());
        const totalWeight = weights.reduce((a, b) => a + b, 0);
        fallRisks = weights.map((w) => 1 - Math.pow(1 - TOTAL_FALL_CHANCE, w / totalWeight));
        holds.forEach((hold, i) => {
            hold.title = `Hold ${i + 1}: ${Math.round(fallRisks[i] * 100)}% chance of falling`;
        });
    }

    // "climbing"    -> working up the holds
    // "falling"     -> slipped, sliding back to the bottom
    // "topped"      -> top hold reached, waiting for the sun to be clicked
    // "celebrating" -> sun reached, smiling sun showing
    let state = "climbing";
    let currentLevel = 0;
    let pulse = null;
    let timers = [];

    // Re-runs the climber's current placement (used when the window is resized).
    let placeClimber = moveToStart;

    // Position the climber with top/left (not bottom) so moves animate smoothly.
    climber.style.bottom = "auto";
    moveToStart();

    // Status message at the bottom of the wall.
    const message = document.createElement("div");
    Object.assign(message.style, {
        position: "absolute",
        bottom: "6px",
        left: "10px",
        right: "10px",
        textAlign: "center",
        color: "white",
        fontSize: "14px",
        fontWeight: "bold",
        textShadow: "0 1px 2px rgba(0,0,0,0.6)",
    });
    wall.appendChild(message);

    // "Climb again" button, shown after the celebration.
    const againButton = document.createElement("button");
    againButton.type = "button";
    againButton.textContent = "Climb again";
    Object.assign(againButton.style, {
        position: "absolute",
        bottom: "40px",
        left: "50%",
        transform: "translateX(-50%)",
        padding: "6px 14px",
        border: "none",
        borderRadius: "16px",
        background: "white",
        color: "#6d5b4c",
        fontWeight: "bold",
        cursor: "pointer",
        boxShadow: "0 2px 6px rgba(0,0,0,0.3)",
        display: "none",
        zIndex: "3",
    });
    againButton.addEventListener("click", reset);
    wall.appendChild(againButton);

    function later(fn, ms) {
        timers.push(setTimeout(fn, ms));
    }

    function moveClimberTo(top, left) {
        climber.style.top = top + "px";
        climber.style.left = left + "px";
    }

    function moveToStart() {
        placeClimber = moveToStart;
        // 30px from the bottom-left corner of the wall.
        moveClimberTo(wall.clientHeight - 30 - climber.offsetHeight, 30);
    }

    function moveOntoHold(hold) {
        placeClimber = () => moveOntoHold(hold);
        const top = hold.offsetTop + hold.offsetHeight / 2 - climber.offsetHeight / 2;
        const left = hold.offsetLeft + hold.offsetWidth / 2 - climber.offsetWidth / 2;
        moveClimberTo(top, left);
    }

    function moveBesideTreasure() {
        // Stand just left of the treasure so the sun stays visible.
        placeClimber = moveBesideTreasure;
        const top = treasure.offsetTop + treasure.offsetHeight - climber.offsetHeight;
        const left = Math.max(4, treasure.offsetLeft - climber.offsetWidth - 4);
        moveClimberTo(top, left);
    }

    function stopPulse() {
        if (pulse) pulse.cancel();
        pulse = null;
    }

    function pulseHold(hold) {
        stopPulse();
        pulse = hold.animate(
            [
                { boxShadow: "0 0 0 0 rgba(255,255,255,0.8)" },
                { boxShadow: "0 0 0 10px rgba(255,255,255,0)" },
            ],
            { duration: 1200, iterations: Infinity }
        );
    }

    function pulseTreasure() {
        stopPulse();
        pulse = treasure.animate(
            [{ scale: "1" }, { scale: "1.2" }, { scale: "1" }],
            { duration: 900, iterations: Infinity }
        );
    }

    function shake(el) {
        el.animate(
            [
                { translate: "0 0" },
                { translate: "-6px 0" },
                { translate: "6px 0" },
                { translate: "-4px 0" },
                { translate: "0 0" },
            ],
            { duration: 350 }
        );
    }

    function bounce(el) {
        el.animate(
            [
                { scale: "1", rotate: "0deg" },
                { scale: "1.7", rotate: "-12deg" },
                { scale: "1.3", rotate: "10deg" },
                { scale: "1", rotate: "0deg" },
            ],
            { duration: 800, easing: "ease-out" }
        );
    }

    function confetti(count) {
        const pieces = ["🎉", "✨", "⭐", "🎊"];
        const originX = treasure.offsetLeft + treasure.offsetWidth / 2;
        const originY = treasure.offsetTop + treasure.offsetHeight / 2;
        for (let i = 0; i < count; i++) {
            const bit = document.createElement("span");
            bit.textContent = pieces[i % pieces.length];
            Object.assign(bit.style, {
                position: "absolute",
                left: originX + "px",
                top: originY + "px",
                fontSize: "20px",
                pointerEvents: "none",
                zIndex: "4",
            });
            wall.appendChild(bit);
            const angle = Math.random() * Math.PI * 2;
            const distance = 60 + Math.random() * 90;
            const dx = Math.cos(angle) * distance;
            const dy = Math.abs(Math.sin(angle)) * distance; // mostly fall downward
            bit.animate(
                [
                    { transform: "translate(0, 0) scale(0.6)", opacity: 1 },
                    { transform: `translate(${dx}px, ${dy}px) scale(1.1)`, opacity: 0 },
                ],
                { duration: 1400 + Math.random() * 600, easing: "ease-out" }
            ).onfinish = () => bit.remove();
        }
    }

    // Put everything back at the bottom, ready for a new climb.
    function startClimb(text) {
        state = "climbing";
        currentLevel = 0;
        rollFallRisks();
        holds.forEach((h) => (h.style.background = holdColor));
        if (treasure) treasure.textContent = "☀️";
        againButton.style.display = "none";
        moveToStart();
        message.textContent = text;
        pulseHold(holds[0]);
    }

    function reset() {
        timers.forEach(clearTimeout);
        timers = [];
        startClimb("Click the holds from the bottom up!");
    }

    function fall() {
        state = "falling";
        stopPulse();
        message.textContent = "Aaah! He slipped!";

        // Reach for the hold, then drop fast and spin on the way down.
        later(() => {
            climber.style.transition = "top 0.7s ease-in, left 0.7s ease-in";
            climber.animate(
                [{ rotate: "0deg" }, { rotate: "540deg" }],
                { duration: 700, easing: "ease-in" }
            );
            moveToStart();
        }, 450);

        later(() => {
            climber.style.transition = ""; // back to the normal move speed from style.css
            shake(climber);
            startClimb("Ouch! He fell. Try again from the bottom!");
        }, 1200);
    }

    function reachSun() {
        state = "celebrating";
        stopPulse();
        moveBesideTreasure();
        message.textContent = "Reaching for the sun...";

        // Wait for the climber to arrive (0.5s transition), then make the sun smile.
        later(() => {
            treasure.textContent = "🌞";
            bounce(treasure);
            confetti(16);
            message.textContent = "You sent it! 🎉";
        }, 550);

        later(() => {
            againButton.style.display = "block";
        }, 3000);
    }

    holds.forEach((hold, index) => {
        hold.addEventListener("click", () => {
            if (state !== "climbing") return;

            if (index !== currentLevel) {
                shake(hold);
                message.textContent = "Not that one, try the next hold up!";
                return;
            }

            moveOntoHold(hold);

            if (Math.random() < fallRisks[index]) {
                fall();
                return;
            }

            currentLevel++;
            hold.style.background = reachedColor;

            if (currentLevel === lastLevel) {
                if (treasure) {
                    state = "topped";
                    message.textContent = "Top out! Click the sun to reach it!";
                    pulseTreasure();
                } else {
                    state = "celebrating";
                    message.textContent = "Top out! You sent it!";
                    againButton.style.display = "block";
                }
            } else {
                message.textContent = "Nice! " + (lastLevel - currentLevel) + " to go.";
                pulseHold(holds[currentLevel]);
            }
        });
    });

    if (treasure) {
        treasure.style.cursor = "pointer";
        treasure.addEventListener("click", () => {
            if (state === "topped") {
                reachSun();
            } else if (state === "celebrating") {
                // Clicking the sun again just celebrates some more.
                bounce(treasure);
                confetti(8);
            } else {
                shake(treasure);
                message.textContent = "Climb all " + lastLevel + " holds to reach the sun!";
            }
        });
    }

    // The holds move when the window is resized, so keep the climber on its spot.
    window.addEventListener("resize", () => placeClimber());

    reset();
});
