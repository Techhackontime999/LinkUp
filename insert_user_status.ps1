$lines = Get-Content 'linkup/messaging/consumers.py'
$insertPos = $null
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -like '*async def read_receipt_update(self, event):*' -and $i -gt 1000) {
        $insertPos = $i
        break
    }
}
if ($insertPos) {
    $handler = @(
        ''
        '    async def user_status(self, event):'
        '        """Send user status update to WebSocket"""'
        '        try:'
        '            response = {'
        '                ''type'': ''user_status'','
        '                ''user_id'': event[''user_id''],'
        '                ''username'': event[''username''],'
        '                ''is_online'': event[''is_online'']'
        '            }'
        '            serialized_response = self.json_serializer.safe_serialize(response)'
        '            await self.send(text_data=self.json_serializer.to_json_string(serialized_response))'
        '        except Exception as e:'
        '            MessagingLogger.log_error('
        '                f"Error in user_status handler: {e}",'
        '                context_data={"event": event, "user_id": self.user.id}'
        '            )'
        ''
    )
    $lines = $lines[0..($insertPos-1)] + $handler + $lines[$insertPos..($lines.Count-1)]
    $lines | Set-Content 'linkup/messaging/consumers.py'
    Write-Host 'Inserted user_status handler before read_receipt_update at line' $insertPos
} else {
    Write-Host 'Could not find insertion point'
}
