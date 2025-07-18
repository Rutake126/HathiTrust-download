import os
import re

def main():
    folder = input("请输入要处理的文件夹路径：").strip('"')

    if not os.path.isdir(folder):
        print("路径不存在，请检查后再试。")
        return

    # 匹配要删除的文件：两个下划线
    delete_pattern = re.compile(r"nyp\.33433082168125-seq_\d+_\d+\.jpg$")

    deleted_count = 0

    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)

        if not os.path.isfile(filepath):
            continue

        if delete_pattern.fullmatch(filename):
            os.remove(filepath)
            print(f"已删除：{filename}")
            deleted_count += 1

    print(f"\n去重完成，共删除 {deleted_count} 个文件。")

if __name__ == "__main__":
    main()
