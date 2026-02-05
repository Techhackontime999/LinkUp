$lines = Get-Content 'linkup/messaging/consumers.py'
$insertPos = $null
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -like '*async def multi_tab_sync(self, event):*' -and $i -gt 1000) {
        $insertPos = $i
        break
    }
}
if ($insertPos) {
    $handler = @(
        ''
        '    async def read_receipt_update(self, event):'
        '        """Send read receipt update to WebSocket"""'
        '        try:'
        '            serialized_message = self.json_serializer.safe_serialize(event["message"])'
        '            await self.send(text_data=self.json_serializer.to_json_string(serialized_message))'
        '        except Exception as e:'
        '            MessagingLogger.log_error('
        '                f"Error in read_receipt_update handler: {e}",'
        '                context_data={"event": event, "user_id": self.user.id}'
        '            )'
        ''
    )
    $lines = $lines[0..($insertPos-1)] + $handler + $lines[$insertPos..($lines.Count-1)]
    $lines | Set-Content 'linkup/messaging/consumers.py'
    Write-Host 'Inserted read_receipt_update handler at line' $insertPos
} else {
    Write-Host 'Could not find insertion point'
}
