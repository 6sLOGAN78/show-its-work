# How It Works: System Architecture (Interview Q&A)

Here’s a behind-the-scenes look at how we actually built the engine, explained exactly how we’d talk about it in an interview or a design review. 

---

### Q: How do you know if a drop in the numbers is actually a real problem, and not just normal seasonal noise?
**A:** That’s exactly where we start, because alert fatigue is a massive issue in the enterprise. Before we even wake the AI up, we run the data through what we call the "Statistical Gate." It’s a pure Python script that strips out normal weekly seasonality—like the fact that sales almost always drop on Sundays. Then it runs a super strict math test called a Median Absolute Deviation (MAD) Z-score. If the drop isn't statistically significant, or if it's just a tiny dip in actual dollars, the engine just stops and says, "Nothing to see here." We don't waste time or money asking an LLM to explain a non-issue.

### Q: Okay, so a real drop is confirmed. How do you figure out what actually caused it?
**A:** This is where our "Proposer" steps in. It mathematically slices and dices the data to see where the bleeding is coming from. It does a waterfall breakdown—basically looking at the total loss and saying, "Okay, we lost $100k, and exactly $75k of that came from this one specific seller." 

### Q: But how do you avoid being tricked by things like Simpson's Paradox, where the data looks like a drop but it's really just a mix shift?
**A:** We're really proud of this part. Sometimes, a metric drops just because a high-volume, low-margin product suddenly sold more than usual. To an AI, that looks like a performance drop. We explicitly programmed a guard against this. The engine splits the data into "within-group effects" and "mix effects." If it realizes the drop is just because of a shift in the mix of what's selling, it flags a `simpson_risk` and stops the system from blaming a false driver. 

### Q: Just because a seller had a bad week at the same time revenue dropped doesn't mean one caused the other. How do you prove it's not just a coincidence?
**A:** Exactly! That’s why we built the "Skeptic." The Skeptic basically plays devil's advocate. Just because a competitor ran a flash sale the same week our revenue dropped, doesn't mean the flash sale caused it. The Skeptic runs four hard math tests to try and kill the hypothesis. For example, it runs a Control Group test. If the competitor flash sale really caused our revenue drop, then *every* seller on our platform should have dropped. If the Skeptic sees that only *one* seller dropped and the rest of the market was fine, it kills the flash sale theory immediately. It also runs a counterfactual test: "If we delete this bad seller from the dataset, does the revenue drop disappear?" If yes, we've found our culprit.

### Q: What happens if the data is just too messy or contradictory?
**A:** Then we do something most AI systems refuse to do: we admit we don't know. Our "Judge" agent scores the surviving evidence on a strict rubric. If the drop is too diffuse—meaning no single seller or category is to blame—or if the evidence is pointing in two different directions, the Judge hits the brakes. It outputs an `INSUFFICIENT` verdict. In the real world, it is infinitely better for an AI to say "I don't have enough data to tell you why this happened" than to hallucinate a plausible-sounding lie.

### Q: You've mentioned the LLM doesn't do the math. So how does the final report actually get written?
**A:** Right, the golden rule of this project is that the LLM *never* computes a number. Once the Python backend finishes all the math and proving the root cause, it creates a locked, completely deterministic "Fact Pack." We then hand that Fact Pack to Gemini and basically say, "Hey, turn these hard facts into a nice, readable memo for the Ops Lead." After Gemini writes the memo, our Verifier runs a regex scan over the text. If it finds that the LLM hallucinated a number or made up a citation that wasn't in the Fact Pack, it flags it. The math is done in Python; the AI just acts as the translator. 
