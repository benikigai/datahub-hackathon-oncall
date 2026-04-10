# DataHub × Nebius Hackathon — Fine-Tune Seed Pairs

> The 8 hand-crafted "perfect" NL→GraphQL examples that anchor the DeepSeek-R1 batch generator.
> Each one represents one of the 8 query patterns the agents need.
> Feed all 8 to R1 as few-shot examples; tell it to generate 30+ variations of one pattern at a time.

## Ground truth: dataset names + URN format

The kit's DataHub ingestion creates these entities under platform `sqlite`:

**Platform instances:**
- `olist_source` — clean Kaggle data, the "ground truth" reference
- `olist_dirty` — same schema, 3 planted quality issues (deleted customers, truncated seller_ids, NULL categories)

**14 datasets per instance** (9 base tables + 5 views, no `_dataset` suffix):

| Type | Names |
|---|---|
| Tables (9) | `olist_customers`, `olist_orders`, `olist_order_items`, `olist_order_payments`, `olist_order_reviews`, `olist_products`, `olist_sellers`, `olist_geolocation`, `product_category_name_translation` |
| Views (5) | `v_order_details`, `v_order_payments`, `v_order_reviews`, `v_seller_performance`, `v_product_sales` |

**URN format (CANONICAL — never deviate):**
```
urn:li:dataset:(urn:li:dataPlatform:sqlite,<instance>.<table>,PROD)
```

Example: `urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.olist_order_items,PROD)`

---

## The 8 seed pairs

Each pair below is JSONL — copy them into `seeds.jsonl` exactly as shown. They are the few-shot prompt for batch generation.

### Pattern 1 — `search_by_name`
Find a dataset URN given a fuzzy or exact name.

```jsonl
{"pattern": "search_by_name", "nl": "Find the dataset for the seller performance view in olist_dirty", "graphql": "{ search(input: {type: DATASET, query: \"v_seller_performance\", start: 0, count: 5}) { searchResults { entity { urn ... on Dataset { name platform { name } } } } } }"}
```

### Pattern 2 — `search_by_tag`
Find datasets matching a tag, glossary term, or platform instance.

```jsonl
{"pattern": "search_by_tag", "nl": "List every dataset in olist_source tagged as PII", "graphql": "{ search(input: {type: DATASET, query: \"tags:urn\\\\:li\\\\:tag\\\\:PII AND platformInstance:olist_source\", start: 0, count: 50}) { searchResults { entity { urn ... on Dataset { name } } } } }"}
```

### Pattern 3 — `get_dataset_details`
Pull schema, description, owners, and tags for one dataset by URN.

```jsonl
{"pattern": "get_dataset_details", "nl": "Get the schema, owners, and tags for olist_customers in olist_source", "graphql": "{ dataset(urn: \"urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_source.olist_customers,PROD)\") { name description schemaMetadata { fields { fieldPath nativeDataType nullable description } } ownership { owners { owner { urn } } } tags { tags { tag { urn } } } } }"}
```

### Pattern 4 — `lineage_upstream`
Trace what feeds into a dataset, N hops upstream.

```jsonl
{"pattern": "lineage_upstream", "nl": "What tables feed into v_product_sales in olist_dirty, 2 hops upstream?", "graphql": "{ lineage(input: {urn: \"urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.v_product_sales,PROD)\", direction: UPSTREAM, count: 100, hops: 2}) { count entities { entity { urn } degree } } }"}
```

### Pattern 5 — `lineage_downstream`
Trace what consumes a dataset, N hops downstream.

```jsonl
{"pattern": "lineage_downstream", "nl": "What views consume olist_order_items in olist_dirty?", "graphql": "{ lineage(input: {urn: \"urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.olist_order_items,PROD)\", direction: DOWNSTREAM, count: 100, hops: 2}) { count entities { entity { urn } degree } } }"}
```

### Pattern 6 — `assertions_with_results`
All quality checks on a dataset + their latest pass/fail.

```jsonl
{"pattern": "assertions_with_results", "nl": "Show me all assertions and their latest results for olist_order_items in olist_dirty", "graphql": "{ dataset(urn: \"urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.olist_order_items,PROD)\") { assertions(start: 0, count: 50) { assertions { urn info { type datasetAssertion { scope operator fields { path } parameters { value { stringValue } } } description } runEvents(limit: 1) { runEvents { timestampMillis status result { type actualAggValue } } } } } } }"}
```

### Pattern 7 — `failing_assertions`
Find datasets where the latest assertion run failed.

```jsonl
{"pattern": "failing_assertions", "nl": "Which datasets in olist_dirty have failing assertions right now?", "graphql": "{ search(input: {type: DATASET, query: \"platformInstance:olist_dirty\", start: 0, count: 100}) { searchResults { entity { urn ... on Dataset { name assertions(start: 0, count: 50) { assertions { runEvents(limit: 1) { runEvents { result { type } } } } } } } } } }"}
```

### Pattern 8 — `column_metadata`
Column-level details for a specific dataset.

```jsonl
{"pattern": "column_metadata", "nl": "Get the column metadata for seller_id in olist_order_items, including the field type and nullability", "graphql": "{ dataset(urn: \"urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.olist_order_items,PROD)\") { schemaMetadata { fields { fieldPath nativeDataType nullable description glossaryTerms { terms { term { urn } } } } } } }"}
```

---

## How to use these for generation

### The R1 meta-prompt (`gen_prompt.txt`)

```
You are generating training data for a fine-tuned NL→GraphQL translator.
Target system: DataHub Core, with these Olist datasets ingested under sqlite:

  Platform instances: olist_source (clean), olist_dirty (planted issues)
  Tables (9): olist_customers, olist_orders, olist_order_items, olist_order_payments,
              olist_order_reviews, olist_products, olist_sellers, olist_geolocation,
              product_category_name_translation
  Views (5):  v_order_details, v_order_payments, v_order_reviews,
              v_seller_performance, v_product_sales

URN format (NEVER deviate):
  urn:li:dataset:(urn:li:dataPlatform:sqlite,<instance>.<table>,PROD)

Here are 8 perfect examples covering all 8 query patterns:

[PASTE ALL 8 SEED PAIRS HERE]

Now generate 30 NEW training pairs for pattern "<PATTERN_NAME>".
Rules:
- Vary the NL phrasing significantly (formal, casual, terse, conversational)
- Vary the dataset/table targeted across all 14 datasets and both instances
- Vary parameter values where applicable (hops 1-3, count 10-100, different filters)
- Output ONLY valid JSONL, one pair per line, with keys "pattern", "nl", "graphql"
- No explanation, no markdown fences, no preamble
```

### Generation script

```bash
mkdir -p ./training_data
> ./training_data/raw_pairs.jsonl

for pattern in search_by_name search_by_tag get_dataset_details \
               lineage_upstream lineage_downstream assertions_with_results \
               failing_assertions column_metadata; do
  echo "Generating for $pattern..."
  curl -s https://api.studio.nebius.com/v1/chat/completions \
    -H "Authorization: Bearer $NEBIUS_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg pat "$pattern" --rawfile prompt gen_prompt.txt '{
      model: "deepseek-ai/DeepSeek-R1-0528",
      max_tokens: 8000,
      temperature: 0.7,
      messages: [{
        role: "user",
        content: ($prompt | sub("<PATTERN_NAME>"; $pat))
      }]
    }')" \
    | jq -r '.choices[0].message.content' \
    >> ./training_data/raw_pairs.jsonl
done

wc -l ./training_data/raw_pairs.jsonl  # should be ~240-300 (R1 occasionally drops some)
```

### Validation script (`validate_pairs.py`)

```python
import json, os, sys, requests
from gql import gql

DATAHUB = "http://100.114.31.63:8080/api/graphql"
TOKEN = open(os.path.expanduser("~/.config/openclaw/datahub_pat")).read().strip()
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def validate(pair):
    try:
        gql(pair["graphql"])
    except Exception as e:
        return False, f"parse: {e}"
    try:
        r = requests.post(DATAHUB, json={"query": pair["graphql"]}, headers=HEADERS, timeout=10)
    except Exception as e:
        return False, f"http: {e}"
    if r.status_code != 200:
        return False, f"http {r.status_code}"
    body = r.json()
    if "errors" in body:
        return False, f"gql: {body['errors'][0]['message']}"
    return True, "ok"

src, dst = sys.argv[1], sys.argv[2]
valid = invalid = 0
with open(src) as f, open(dst, "w") as out:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            p = json.loads(line)
        except json.JSONDecodeError:
            invalid += 1; continue
        ok, msg = validate(p)
        if ok:
            out.write(json.dumps(p) + "\n"); valid += 1
        else:
            invalid += 1
            print(f"DROP [{p.get('pattern','?')}]: {msg[:120]}")

print(f"\n{valid} valid, {invalid} dropped, kept {valid/(valid+invalid)*100:.0f}%")
```

Run: `python validate_pairs.py training_data/raw_pairs.jsonl training_data/validated_pairs.jsonl`

Expected drop rate: 15-30%. Target: 200+ validated pairs after filtering.

### JSONL chat reformat + 80/20 split

```python
# format_for_nebius.py
import json, random

SYSTEM = (
    "You translate natural language questions about data assets into DataHub "
    "GraphQL read queries. The target is DataHub Core with Olist datasets ingested "
    "under sqlite platform instances olist_source (clean) and olist_dirty (planted "
    "issues). URN format is urn:li:dataset:(urn:li:dataPlatform:sqlite,"
    "<instance>.<table>,PROD). Return only valid GraphQL, no markdown, no explanation."
)

with open("training_data/validated_pairs.jsonl") as f:
    pairs = [json.loads(l) for l in f if l.strip()]

random.seed(42)
random.shuffle(pairs)

split = int(len(pairs) * 0.8)
train, val = pairs[:split], pairs[split:]

def to_chat(p):
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": p["nl"]},
        {"role": "assistant", "content": p["graphql"]},
    ]}

with open("training_data/train.jsonl", "w") as f:
    for p in train: f.write(json.dumps(to_chat(p)) + "\n")
with open("training_data/val.jsonl", "w") as f:
    for p in val: f.write(json.dumps(to_chat(p)) + "\n")

print(f"train: {len(train)} pairs, val: {len(val)} pairs")
```

Output files: `training_data/train.jsonl` and `training_data/val.jsonl` — these are what you upload to Nebius Data Lab.

---

## What to ship to Nebius

Two files, ~2-5 MB total:
- `train.jsonl` — ~200-240 pairs in OpenAI chat format
- `val.jsonl` — ~50-60 pairs in OpenAI chat format

Upload via Nebius Studio → Data Lab → Datasets → Upload. Each becomes a `dataset_id` to reference in the LoRA training job.
