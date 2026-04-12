import sys
sys.path.insert(0, "/opt/dlogic/netkeita-api")
from services.data_fetcher import get_stable_comments

# Test 20260404 中山 multiple races
for r in [1, 5, 11]:
    result = get_stable_comments("20260404", "中山", r)
    if result:
        print(f"20260404 中山{r}R: {len(result)} horses")
        sample = list(result.items())[0]
        print(f"  sample: #{sample[0]} mark={sample[1].get('mark','')} comment={sample[1].get('comment','')[:50]}")
    else:
        print(f"20260404 中山{r}R: NO DATA")

# Test 阪神 too
for r in [1, 11]:
    result = get_stable_comments("20260404", "阪神", r)
    if result:
        print(f"20260404 阪神{r}R: {len(result)} horses")
    else:
        print(f"20260404 阪神{r}R: NO DATA")
