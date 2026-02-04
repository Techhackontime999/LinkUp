# Layout Debug Guide

## Current Structure (Should be correct now)

```html
<div class="grid grid-cols-1 lg:grid-cols-12">  <!-- Line 5: Main Grid Opens -->
    
    <!-- Left Sidebar (col-span-3) -->
    <div class="hidden lg:block lg:col-span-3">  <!-- Line 7 -->
        ...Profile Card...
    </div>  <!-- Left sidebar closes -->
    
    <!-- Main Feed (col-span-6) -->
    <div class="lg:col-span-6">  <!-- Line 38 -->
        ...Composer...
        ...Posts...
        ...Pagination...
    </div>  <!-- Line 349: Main feed closes -->
    
    <!-- Right Sidebar (col-span-3) -->
    <div class="hidden lg:block lg:col-span-3">  <!-- Line 351 -->
        ...Trending Topics (sticky)...
    </div>  <!-- Line 385: Right sidebar closes -->
    
</div>  <!-- Line 387: Main Grid Closes -->
```

## If Still Not Working - Try These Steps:

### 1. Clear Browser Cache
```
Ctrl + Shift + Delete (Windows/Linux)
Cmd + Shift + Delete (Mac)
```
Or hard refresh: `Ctrl + F5` (Windows) / `Cmd + Shift + R` (Mac)

### 2. Collect Static Files (if using production)
```bash
cd linkup
python manage.py collectstatic --noinput
```

### 3. Restart Django Server
```bash
# Stop server (Ctrl + C)
# Then restart
python manage.py runserver
```

### 4. Check Browser Console
Open Developer Tools (F12) and check:
- Console tab for JavaScript errors
- Elements tab to inspect the actual HTML structure
- Look for the grid classes: `grid-cols-1 lg:grid-cols-12`

### 5. Verify Tailwind CSS is Loading
In browser DevTools:
- Check if the `lg:col-span-3` and `lg:col-span-6` classes are being applied
- Look in the Network tab to ensure CSS files are loading

### 6. Test on Different Screen Sizes
- Desktop (> 1024px): Should show 3 columns
- Tablet (768px - 1024px): Should show 2 columns  
- Mobile (< 768px): Should show 1 column

## Expected Layout on Desktop (lg screens):

```
┌──────────────┬─────────────────┬──────────────┐
│              │                 │              │
│   Profile    │    Composer     │   Trending   │
│   (Sticky)   │                 │   (Sticky)   │
│              │    Post 1       │              │
│              │    Post 2       │              │
│              │    Post 3       │              │
│              │    ...          │              │
│              │    Pagination   │              │
│              │                 │              │
└──────────────┴─────────────────┴──────────────┘
   col-span-3      col-span-6       col-span-3
```

## If Trending Topics Still Appears Below:

This means the grid is not working. Check:

1. **Is Tailwind CSS loaded?**
   - View page source
   - Look for `<link>` tag with tailwind CSS
   
2. **Are breakpoints correct?**
   - `lg:` prefix means >= 1024px
   - Make sure your browser window is wide enough

3. **Is there a CSS conflict?**
   - Check if custom CSS is overriding grid layout
   - Look in `custom_styles.css` for any conflicting rules

## Manual Fix (if nothing works):

If the issue persists, you can try adding inline styles temporarily:

```html
<div class="grid grid-cols-1 lg:grid-cols-12" style="display: grid; grid-template-columns: repeat(12, minmax(0, 1fr));">
```

This will force the grid layout even if Tailwind isn't working properly.
