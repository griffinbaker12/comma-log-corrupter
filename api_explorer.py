import requests

ACCOUNT, DEVICE, ROUTE = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NDg1ODI0NjUsIm5iZiI6MTcxNzA0NjQ2NSwiaWF0IjoxNzE3MDQ2NDY1LCJpZGVudGl0eSI6IjBkZWNkZGNmZGYyNDFhNjAifQ.g3khyJgOkNvZny6Vh579cuQj1HLLGSDeauZbfZri9jw",
    "1d3dc3e03047b0c7",
    "000000dd--455f14369d",
)

files = requests.get(
    f"https://api.commadotai.com/v1/route/{DEVICE}|{ROUTE}/files",
    headers={"Authorization": f"JWT {ACCOUNT}"},
).json()

print(files)
