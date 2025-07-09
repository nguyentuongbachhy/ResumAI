import os

def build_tree(dir_path, prefix=''):
    entries = sorted(os.listdir(dir_path))
    entries = [e for e in entries if e not in {'.git', '__pycache__', 'structure.md', 'get_structure.py', '.gitignore', '.env', 'mlruns', 'wandb'}]
    lines = []
    for index, entry in enumerate(entries):
        path = os.path.join(dir_path, entry)
        connector = '└── ' if index == len(entries) - 1 else '├── '
        lines.append(f"{prefix}{connector}{entry}")
        if os.path.isdir(path) and entry != 'node_modules':
            extension = '    ' if index == len(entries) - 1 else '│   '
            lines.extend(build_tree(path, prefix + extension))
    return lines

if __name__ == '__main__':
    tree_lines = ["# Cấu trúc thư mục\n"]
    tree_lines.extend(build_tree('./'))

    output_path = './structure.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(tree_lines))

    print(f"Đã lưu cấu trúc thư mục vào {output_path}")
