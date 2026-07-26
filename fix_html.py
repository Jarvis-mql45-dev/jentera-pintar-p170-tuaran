with open(r'c:\Users\Admin\Documents\Krist Mazmiel\JenteraPintar_P170 Tuaran\frontend\index.html', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('value="100" min="0" max="200" class="w-10 text-center font-bold text-black border border-gray-300 rounded px-0.5" style="display:inline-block;"', 'value="50" min="0" max="200" class="w-10 text-center font-bold text-black border border-gray-300 rounded px-0.5" style="display:inline-block;"')
with open(r'c:\Users\Admin\Documents\Krist Mazmiel\JenteraPintar_P170 Tuaran\frontend\index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done - index.html updated')