import json

with open('bitfly.log') as rfile:
  lines = rfile.readlines()

msg_types = ('ReceiveTickers', 'addNewMessageToPage')

# Return None is no valid book date can be found.
def iter_book_data(raw_message):
  payload_message = raw_message.get('M')
  if not payload_message:
    return

  for msg_elem in payload_message:
    assert msg_elem['H'] == 'BFEXHub', msg_elem
    if msg_elem['M'] != 'ReceiveTickers':
      continue
    assert len(msg_elem['A']) == 1, len(msg_elem['A'])
    for book_msg in msg_elem['A'][0]:
      yield book_msg


def parse_message(message):
  msg = json.loads(message)
  fetch_time = msg['fetch_time']
  l = [m for m in msg['M'] if m['M'] == msg_types[0]]
  for m in l:
    assert len(m['A']) == 1, len(m['A'])
    for n in m['A'][0]:
      print(json.dumps(n, indent=2))
      print()


for line in lines:
  line = json.loads(line)
  for msg in iter_book_data(line):
    print(json.dumps(msg, indent=2))
    print()
