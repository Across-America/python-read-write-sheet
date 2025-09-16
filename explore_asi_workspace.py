# 探索 ASI 工作区
import smartsheet
import os

print("正在连接到 Smartsheet...")

# 使用环境变量中的 token
smart = smartsheet.Smartsheet()
smart.errors_as_exceptions(True)

# ASI 工作区 ID
asi_workspace_id = 2580314045343620

def list_folder_contents(folder_id, folder_name):
    """列出文件夹中的内容"""
    try:
        print(f'\n📁 正在查看文件夹: {folder_name}')
        print('=' * 50)
        
        # 获取文件夹中的工作表
        try:
            sheets = smart.Folders.list_sheets(folder_id)
            if sheets.data:
                print(f'📊 工作表 ({len(sheets.data)} 个):')
                for i, sheet in enumerate(sheets.data, 1):
                    print(f'  {i}. {sheet.name} (ID: {sheet.id})')
            else:
                print('📊 没有工作表')
        except Exception as e:
            print(f'获取工作表失败: {e}')
        
        # 获取文件夹中的子文件夹
        try:
            subfolders = smart.Folders.list_folders(folder_id)
            if subfolders.data:
                print(f'📁 子文件夹 ({len(subfolders.data)} 个):')
                for i, subfolder in enumerate(subfolders.data, 1):
                    print(f'  {i}. {subfolder.name} (ID: {subfolder.id})')
            else:
                print('📁 没有子文件夹')
        except Exception as e:
            print(f'获取子文件夹失败: {e}')
            
    except Exception as e:
        print(f'查看文件夹 {folder_name} 时出错: {e}')

try:
    print(f'\n=== ASI 工作区结构 ===')
    print(f'工作区ID: {asi_workspace_id}')
    print('=' * 60)
    
    # 获取根级别的文件夹
    folders = smart.Workspaces.list_folders(asi_workspace_id)
    
    if folders.data:
        print(f'🏠 根级别文件夹 ({len(folders.data)} 个):')
        print('-' * 40)
        for i, folder in enumerate(folders.data, 1):
            print(f'{i}. {folder.name} (ID: {folder.id})')
        
        print('\n' + '='*60)
        print('详细内容:')
        
        # 查看每个文件夹的内容
        for folder in folders.data:
            list_folder_contents(folder.id, folder.name)
    else:
        print('📁 没有找到文件夹')
    
    # 尝试获取根级别的工作表
    try:
        print(f'\n🏠 根级别工作表:')
        print('=' * 50)
        # 这里可能需要不同的方法来获取根级别工作表
        print('正在尝试获取根级别工作表...')
    except Exception as e:
        print(f'获取根级别工作表时出错: {e}')

except Exception as e:
    print(f'错误: {e}')
    print('请确保您有访问该工作区的权限')
