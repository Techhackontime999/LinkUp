# CKEditor Usage Guide - Edit Post Feature

## Hindi/English Mixed Guide (आसान समझ के लिए)

### क्या बदला है? (What Changed?)

अब जब आप अपनी post को edit करेंगे, तो आपको एक rich text editor मिलेगा जिसमें formatting options होंगे।

**पहले (Before):**
- Simple textarea था
- कोई formatting नहीं कर सकते थे
- Plain text ही लिख सकते थे

**अब (Now):**
- CKEditor के साथ rich text editor
- Bold, Italic, Lists, Links जैसे options
- Professional formatting के साथ post edit कर सकते हैं

---

## कैसे Use करें? (How to Use?)

### Step 1: Edit Post खोलें
1. अपनी post पर जाएं
2. 3 dots (⋮) पर click करें
3. "Edit Post" select करें

### Step 2: CKEditor का Use करें
Modal खुलने पर आपको formatting toolbar दिखेगा:

```
[B] [I] [U] [S] | [1.] [•] ["] | [🔗] | [📷] [📊] | [Format ▼] | [⛶]
```

#### Formatting Options:

**Text Formatting:**
- **B** = Bold (मोटा text)
- **I** = Italic (तिरछा text)
- **U** = Underline (नीचे line)
- **S** = Strike-through (बीच में line)

**Lists:**
- **1.** = Numbered list (1, 2, 3...)
- **•** = Bullet list (• • •)

**Other:**
- **"** = Blockquote (quote highlight करने के लिए)
- **🔗** = Add/Remove links
- **📷** = Insert image
- **📊** = Insert table
- **Format ▼** = Heading styles (H1, H2, etc.)
- **⛶** = Maximize (full screen mode)

### Step 3: Content Edit करें
1. अपना content type/edit करें
2. जहां चाहें formatting apply करें
3. "Save Changes" button पर click करें

---

## Examples (उदाहरण)

### Example 1: Bold Text बनाना
1. Text select करें
2. **B** button पर click करें
3. Text bold हो जाएगा

### Example 2: List बनाना
1. Cursor को जहां list चाहिए वहां रखें
2. **•** (bullet) या **1.** (numbered) पर click करें
3. Items type करें, Enter press करें नई item के लिए

### Example 3: Link Add करना
1. Text select करें जिसे link बनाना है
2. **🔗** button पर click करें
3. URL enter करें
4. OK पर click करें

---

## Tips & Tricks

### ✨ Pro Tips:
1. **Keyboard Shortcuts:**
   - Ctrl+B = Bold
   - Ctrl+I = Italic
   - Ctrl+U = Underline
   - Ctrl+K = Add link

2. **Full Screen Mode:**
   - ⛶ button click करें बड़े editor के लिए
   - Escape press करें वापस आने के लिए

3. **Copy-Paste:**
   - Formatted text को copy-paste कर सकते हैं
   - Formatting automatically adjust हो जाएगी

### ⚠️ ध्यान दें (Important Notes):
- Content automatically save नहीं होता - "Save Changes" जरूर click करें
- Image upload करने से पहले size check करें (max 50MB)
- बहुत ज्यादा formatting से avoid करें - simple और readable रखें

---

## Troubleshooting (समस्या समाधान)

### Problem 1: CKEditor नहीं दिख रहा
**Solution:**
```bash
# Browser cache clear करें
Ctrl + Shift + R (hard reload)

# या terminal में:
cd linkup
python3 manage.py collectstatic --noinput
```

### Problem 2: Formatting save नहीं हो रही
**Solution:**
- Check करें कि "Save Changes" button click किया है
- Browser console में errors check करें (F12 press करें)
- Page reload करके फिर से try करें

### Problem 3: Content गायब हो गया
**Solution:**
- Modal close करने से पहले save करें
- अगर accidentally close हो गया, तो फिर से edit करें
- Original content database में safe है

---

## Visual Guide (देखने में कैसा दिखेगा)

### Before (पहले):
```
┌─────────────────────────────────────┐
│ Edit Post                        [X]│
├─────────────────────────────────────┤
│ Content:                            │
│ ┌─────────────────────────────────┐ │
│ │ This is my post content...      │ │
│ │                                 │ │
│ │                                 │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [Cancel]              [Save Changes]│
└─────────────────────────────────────┘
```

### After (अब):
```
┌─────────────────────────────────────┐
│ Edit Post                        [X]│
├─────────────────────────────────────┤
│ Content:                            │
│ ┌─────────────────────────────────┐ │
│ │ [B][I][U] [•][1.] [🔗] [⛶]     │ │ ← Toolbar
│ ├─────────────────────────────────┤ │
│ │ This is my post content...      │ │
│ │                                 │ │
│ │                                 │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [Cancel]              [Save Changes]│
└─────────────────────────────────────┘
```

---

## Benefits (फायदे)

### For Users:
✅ Professional looking posts
✅ Better content organization
✅ Easy to highlight important points
✅ Add links without showing full URL
✅ Create structured content with lists

### For Platform:
✅ More engaging content
✅ Better user experience
✅ Professional appearance
✅ Competitive with other platforms

---

## Support

अगर कोई problem आए तो:
1. Documentation पढ़ें
2. Test script run करें: `python3 test_edit_ckeditor.py`
3. Browser console check करें (F12)
4. Django logs check करें

---

## Summary (सारांश)

**क्या मिला:**
- Rich text editor for editing posts
- Professional formatting options
- Easy to use toolbar
- Same experience as creating new posts

**कैसे use करें:**
1. Post edit करें
2. Formatting apply करें
3. Save करें
4. Enjoy! 🎉

---

**Happy Editing! 🚀**
