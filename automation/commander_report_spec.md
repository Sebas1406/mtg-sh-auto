# Commander Builder Report V2 Specification

## Source of truth

The report is derived from `deck_manifests/<report_id>.json`. Markdown, JSON, images, the Moxfield export, and the publish queue must all carry the same `deck_hash`.

## Mandatory quality gates

- Exactly 100 cards including one or two commanders.
- A legal command-zone configuration.
- Current paper Commander legality for every card.
- Every card inside the combined commander color identity.
- Singleton by canonical English name, with only rules-defined exceptions.
- Scryfall name, Oracle ID, card data, and image integrity.
- 33–40 lands and sufficient colored mana sources.
- At least 10 ramp, 10 card-advantage, 8 interaction, 2 board wipes, 3 protection, and 3 win-condition contributions.
- Dedicated role caps prevent the list from becoming a pile of removal, ramp, or expensive finishers.
- No more than eight nonland cards with mana value 6+.
- Bracket-compliant Game Changers and casual play patterns.
- Current Wizards policy data. A fallback policy cannot publish.

## Report language and tone

- All report and carousel copy is in English.
- Builder-first and practical.
- Warm, friendly tavern atmosphere with clean execution.
- Only `@sebastianhurtado92` appears as the account identity.
- No fabricated personal anecdotes or visible AI/creator persona.

## Report structure

1. Commander & Deck Promise
2. Deck Skeleton
3. Core Engine
4. Mana & Cards
5. Answers & Protection
6. How It Wins
7. Mulligan & Turn Plan
8. Weaknesses & Budget Swaps
9. Verified Full Decklist
10. Sources and validation metadata

## Public carousel

The carousel contains six 1080×1920 slides:

1. Deck promise, commander art, bracket, total cards, lands, average mana value, and validation badge.
2. Dedicated deck-role counts, mana curve, and validation summary.
3. Four core-engine cards with one-line reasons.
4. Four mana/card-advantage cards with one-line reasons.
5. Four interaction/protection cards with one-line reasons.
6. Four closing cards with one-line reasons and the full-list call to action.

Every displayed card must exist in the canonical mainboard. Price must never determine featured-card priority.
