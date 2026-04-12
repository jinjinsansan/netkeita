import requests

payload = {
    "title": "TEST internal key",
    "body": "test body",
    "description": "test",
    "status": "draft",
    "content_type": "article",
    "tipster_id": "Ufa57350b427392b636d3f9b7c30ead0c",
    "race_id": "",
    "bet_method": "",
    "ticket_count": 0,
    "preview_body": "",
    "is_premium": False,
}
r = requests.post(
    "http://localhost:5002/api/articles",
    json=payload,
    headers={"X-Internal-Key": "lK0qK4UJ6uvD7e9BHL3kYXzdD_pGdmGxFZxhr5jJouA"},
    timeout=10,
)
print(r.status_code, r.text[:400])
