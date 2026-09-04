# Why We Chose PS3: Strategic Q&A

When the Accenture Innovation Challenge dropped the four problem statements, we had a lot to think about. After hashing it out, Team Mandalorians unanimously went with **PS3: BusinessIntelligence.ai**. 

If you asked us in an interview why we picked it, here’s exactly what we'd say.

---

### Q: Out of the four Accenture Innovation Challenge problem statements, why did Team Mandalorians choose PS3?
**A:** We went with PS3 because it sits squarely in the "Foundational Trust Layer" of enterprise AI, rather than just the application layer. If you're building a customer service chatbot and the AI uses a slightly weird adjective, it’s not a big deal—that's "fuzzy" AI. But Business Intelligence is completely different. If a CFO asks why revenue is down by a hundred grand, and the AI hallucinates a digit or points the finger at the wrong department, people lose their jobs and the company loses money. We chose PS3 because we wanted to tackle the hardest, scariest problem in AI right now: How do you build a generative system where executives can actually trust every single number it spits out?

### Q: Did you just build an AI wrapper over a dataset?
**A:** No, and honestly, that was a big reason we picked this problem. A lot of AI hackathon projects just take a CSV, throw it into an LLM with a clever prompt, and ask it for "insights." We knew from day one that approach totally fails in the real world. PS3 gave us the excuse to really flex our computer science and engineering muscles. Instead of just writing prompts, we spent our time building a heavy deterministic backend in Python—writing algorithms for Median Absolute Deviation, building literal mathematical guards against Simpson's Paradox, and creating a "Skeptic" agent that uses control groups to actively try and disprove its own theories. The AI part is just the tip of the iceberg; the real magic is the math underneath it.

### Q: What’s the actual business value (ROI) of solving this specific problem?
**A:** It's massive. Right now, enterprise dashboards are great at telling you *what* happened. An executive logs in and sees, "Okay, revenue is down 10%." But then, human analysts have to spend the next week doing "Slack archaeology"—exporting spreadsheets, messaging different teams, and trying to figure out *why* it happened and *what* to do about it. By solving PS3, we take that week-long, stressful diagnostic process and compress it into about 45 seconds. An engine that can instantly trace a revenue drop down to a specific supplier's SLA failure—without hallucinating—is something any Fortune 500 company would pay serious money for. 

### Q: How does this project show where Generative AI is actually heading?
**A:** We think it proves that the era of the simple "chat window" is kind of over. If we had chosen another problem statement, we might have just built a standard RAG chatbot. But PS3 forced us to build a true multi-agent system. We built an architecture where agents literally debate each other—the Proposer comes up with an idea, the Skeptic tries to tear it down with math, and the Judge decides who won. And most importantly, we programmed it to have the honesty to just say "I don't know" when the data is too messy. We wanted to move past the AI hype and build something mathematically defensible.
