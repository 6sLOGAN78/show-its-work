# How It Works: Under the Hood

Here’s a behind-the-scenes look at how we actually built the engine, explained exactly how we’d talk about it in an interview or a design review. 

### Stopping Alert Fatigue Before It Starts
When you're dealing with enterprise data, alert fatigue is a massive issue. You don't want the AI firing off a panic report every time a metric wiggles. So, before we even wake the AI up, we run the raw data through what we call the "Statistical Gate." It’s a pure Python script that strips out normal weekly seasonality—like the fact that sales almost always drop on Sundays. Then it runs a super strict math test called a Median Absolute Deviation (MAD) Z-score. If the drop isn't statistically significant, or if it's just a tiny dip in actual dollars, the engine just stops and says, "Nothing to see here." We don't waste time or money asking an LLM to explain a non-issue.

### Slicing the Data to Find the Bleeding
Once a real drop is confirmed, our "Proposer" steps in. It mathematically slices and dices the data to see where the bleeding is coming from. It does a waterfall breakdown—basically looking at the total loss and saying, "Okay, we lost $100k, and exactly $75k of that came from this one specific seller." 

### Beating Simpson's Paradox
We're really proud of this next part. Sometimes, a metric drops just because a high-volume, low-margin product suddenly sold more than usual. To an AI, that looks like a performance drop, but it's really just a mix shift. We explicitly programmed a guard against this. The engine splits the data into "within-group effects" and "mix effects." If it realizes the drop is just because of a shift in the mix of what's selling, it flags a `simpson_risk` and stops the system from blaming a false driver. 

### Playing Devil's Advocate
Just because a seller had a bad week at the same time revenue dropped doesn't mean one caused the other. That’s why we built the "Skeptic." The Skeptic basically plays devil's advocate. Just because a competitor ran a flash sale the same week our revenue dropped, doesn't mean the flash sale caused it. The Skeptic runs four hard math tests to try and kill the hypothesis. For example, it runs a Control Group test. If the competitor flash sale really caused our revenue drop, then *every* seller on our platform should have dropped. If the Skeptic sees that only *one* seller dropped and the rest of the market was fine, it kills the flash sale theory immediately. It also runs a counterfactual test: "If we delete this bad seller from the dataset, does the revenue drop disappear?" If yes, we've found our culprit.

### Having the Honesty to Say "I Don't Know"
Sometimes, the data is just too messy or contradictory. When that happens, we do something most AI systems refuse to do: we admit we don't know. Our "Judge" agent scores the surviving evidence on a strict rubric. If the drop is too diffuse—meaning no single seller or category is to blame—or if the evidence is pointing in two different directions, the Judge hits the brakes. It outputs an `INSUFFICIENT` verdict. In the real world, it is infinitely better for an AI to say "I don't have enough data to tell you why this happened" than to hallucinate a plausible-sounding lie.

### The AI is Just the Translator
The golden rule of this project is that the LLM *never* computes a number. Once the Python backend finishes all the math and proves the root cause, it creates a locked, completely deterministic "Fact Pack." We then hand that Fact Pack to Gemini and basically say, "Hey, turn these hard facts into a nice, readable memo for the Ops Lead." After Gemini writes the memo, our Verifier runs a regex scan over the text. If it finds that the LLM hallucinated a number or made up a citation that wasn't in the Fact Pack, it flags it. The math is done in Python; the AI just acts as the translator. 
