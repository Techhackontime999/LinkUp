# Communication Registration Fix

## Issue

When registering an AI agent through the "AI Agent Communication" interface, users could not reuse names from previously deleted agents, even though those agents were soft-deleted.

### Root Cause

The `AgentRegistryService.register_agent()` method was checking for duplicate names across ALL agents in the database:

```python
# OLD CODE (BUGGY)
if AIAgent.objects.filter(name=name).exists():
    return {
        'status': 'FAILED',
        'error': 'Agent name already exists'
    }
```

This included:
- Active agents (`is_active=True`)
- Deleted agents (`is_active=False`)

When an agent is deleted through the admin panel:
1. It's soft-deleted: `is_active=False`
2. Name is renamed with timestamp: `{name}_deleted_{timestamp}`

However, the communication registration was still checking the original name before the rename, causing conflicts.

---

## Fix

Updated the duplicate name check to only consider active agents:

```python
# NEW CODE (FIXED)
if AIAgent.objects.filter(name=name, is_active=True).exists():
    return {
        'status': 'FAILED',
        'error': 'Agent name already exists'
    }
```

---

## File Modified

**File**: `linkup/ai_agents/services.py`

**Function**: `AgentRegistryService.register_agent()`

**Line**: ~58

**Change**: Added `is_active=True` filter to the duplicate name check

---

## Behavior Now

### Before Fix
1. User creates agent "TestBot" via communication interface ✅
2. User deletes "TestBot" via admin panel (soft delete) ✅
3. User tries to create new agent "TestBot" via communication interface ❌ **ERROR: "Agent name already exists"**

### After Fix
1. User creates agent "TestBot" via communication interface ✅
2. User deletes "TestBot" via admin panel (soft delete) ✅
   - Agent renamed to "TestBot_deleted_20260304_123456"
   - Agent marked as `is_active=False`
3. User tries to create new agent "TestBot" via communication interface ✅ **SUCCESS!**

---

## Consistency

This fix makes the communication registration consistent with the admin panel behavior:

| Interface | Duplicate Check | Allows Reusing Deleted Names |
|-----------|----------------|------------------------------|
| Admin Panel (`add_ai_model`) | Only active agents | ✅ Yes |
| Communication (`register_agent`) | ~~All agents~~ → Only active agents | ✅ Yes (FIXED) |

---

## Testing

To verify the fix:

1. **Register an agent via communication interface**:
   - Go to `/api/communication/`
   - Register agent with name "TestAgent123"
   - Note the Platform API Key

2. **Delete the agent via admin panel**:
   - Go to `/api/admin/ai-models/`
   - Find "TestAgent123"
   - Click Delete
   - Verify it's soft-deleted (renamed with timestamp)

3. **Try to register again with same name**:
   - Go back to `/api/communication/`
   - Register new agent with name "TestAgent123"
   - Should succeed ✅

4. **Verify duplicate check still works**:
   - Try to register another agent with name "TestAgent123"
   - Should fail with "Agent name already exists" ❌

---

## Related Code

The admin panel already had this correct behavior:

```python
# linkup/ai_agents/admin_ai_model_views.py (add_ai_model function)
if AIAgent.objects.filter(name=name, is_active=True).exists():
    messages.error(request, 'A model with this name already exists')
    return render(request, 'ai_agents/add_ai_model.html', {'form_data': request.POST})
```

The communication registration now matches this behavior.

---

## Impact

- ✅ Users can now reuse names from deleted agents
- ✅ Duplicate name validation still works for active agents
- ✅ Consistent behavior across admin panel and communication interface
- ✅ No breaking changes to existing functionality
- ✅ Soft delete mechanism still works as expected

---

## Notes

- Deleted agents are renamed with timestamp to free up the name
- The `is_active=False` flag marks them as deleted
- This allows the name to be reused immediately
- The old agent data is preserved for audit/history purposes
