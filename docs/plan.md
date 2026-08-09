# Build plan — Aug 9 → Sept 5

Four weeks, ordered so the riskiest integrations land first and the last week
is buffer + field-testing, not feature work.

## Week 1 (Aug 11–17): backend live end-to-end

- [ ] Provision: Render account + blueprint deploy, Google Places API key,
      Tavily key, generate `API_TOKEN`
- [ ] Deploy the scaffold; `/api/rebuild-index`; verify `/api/chat` answers
      grounded itinerary questions from a phone browser/curl
- [ ] Verify journal flow end-to-end via curl (start → message → confirm →
      finish) with a real Athens restaurant
- [ ] Run all three jobs manually; check `/api/today` and `/api/insights`
- [ ] Fix the itinerary before it becomes the brain: Patmos daytrip logistics,
      allocate days for Veria and Kavala/Philippi

## Week 2 (Aug 18–24): iOS app against the live backend

- [ ] Create the Xcode project, wire in the sources, run on device
- [ ] Ask tab: chat + location chip + memory toggle against production
- [ ] Journal tab: full flow including the Yes/No card
- [ ] Map, Today, Journey tabs rendering live data
- [ ] TestFlight build #1

## Week 3 (Aug 25–31): polish + offline + field drills

- [ ] Offline: cache-serving verified in airplane mode; journal drafts queue
      and sync (finish CacheStore queue + retry)
- [ ] Dress rehearsal days: live on the app for 2 full days locally — journal
      real meals, ask real questions, read the digests
- [ ] Tune prompts from rehearsal transcripts (concierge tone, interview
      questions, insight quality)
- [ ] Pre-generate Mt Athos morning guides (Sept 20–23)
- [ ] Cost check: review API spend from rehearsal, project trip total

## Week 4 (Sept 1–4): freeze + buffer

- [ ] TestFlight build final; no new features after Sept 1
- [ ] Export/backup path for the data disk (daily SQLite copy)
- [ ] Print/save the runbook: Render dashboard, key rotation, how to rerun jobs
- [ ] Slack in the buffer — something above will have slipped

## Sept 5: fly. The app is a companion, not a dependency — every feature
degrades to "look at the itinerary markdown" if the backend has a bad day.
