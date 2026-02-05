import fileinput
import sys

lines = []
with open('linkup/messaging/consumers.py', 'r') as f:
    lines = f.readlines()

# Insert read_receipt_update before multi_tab_sync at NotificationsConsumer (around line 1047)
insert_pos = None
for i, line in enumerate(lines):
    if 'async def multi_tab_sync(self, event):' in line and i > 1000:  # NotificationsConsumer
        insert_pos = i
        break

if insert_pos:
    handler = [
        '\n',
        '    async def read_receipt_update(self, event):\n',
        '        """Send read receipt update to WebSocket"""\n',
        '        try:\n',
        '            serialized_message = self.json_serializer.safe_serialize(event["message"])\n',
        '            await self.send(text_data=self.json_serializer.to_json_string(serialized_message))\n',
        '        except Exception as e:\n',
        '            MessagingLogger.log_error(\n',
        '                f"Error in read_receipt_update handler: {e}",\n',
        '                context_data={"event": event, "user_id": self.user.id}\n',
        '            )\n',
        '\n'
    ]
    lines[insert_pos:insert_pos] = handler

    with open('linkup/messaging/consumers.py', 'w') as f:
        f.writelines(lines)

    print('Inserted read_receipt_update handler at line', insert_pos)
else:
    print('Could not find insertion point')
