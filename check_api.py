"""
API 配置诊断脚本
用于验证 API 密钥配置是否正确
"""
import os
import sys
import traceback

# 添加调试输出
print("正在启动API配置诊断脚本...")

try:
    print("正在导入 get_api_key 函数...")
    from database import get_api_key
    print("成功导入 get_api_key 函数")
except Exception as e:
    print(f"导入 get_api_key 函数时出错: {e}")
    traceback.print_exc()
    sys.exit(1)

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def check_credentials_file():
    """Check if credentials file exists and its content"""
    print_header("检查凭证文件")
    
    credentials_path = "/workspaces/QUIZ_NEW/credentials"
    
    print(f"正在检查凭证文件: {credentials_path}")
    if not os.path.exists(credentials_path):
        print(f"❌ 错误: 凭证文件不存在: {credentials_path}")
        return False
    
    print(f"✅ 凭证文件存在: {credentials_path}")
    
    # Print file contents
    print("\n凭证文件内容:")
    print("-" * 40)
    try:
        with open(credentials_path, "r") as f:
            content = f.read()
            print(content)
    except Exception as e:
        print(f"❌ 读取凭证文件时出错: {e}")
        return False
    print("-" * 40)
    
    return True

def test_api_key_retrieval():
    """Test retrieving API keys using get_api_key function"""
    print_header("测试 API 密钥检索")
    
    try:
        # Test DEEPSEEK API key
        print("尝试获取 DEEPSEEK API 密钥...")
        deepseek_key = get_api_key("DEEPSEEK", "DEEPSEEK_API_KEY")
        if deepseek_key:
            masked_key = deepseek_key[:5] + "..." + deepseek_key[-4:] if len(deepseek_key) > 10 else "***"
            print(f"✅ 成功获取 DEEPSEEK API 密钥: {masked_key}")
        else:
            print("❌ 未能获取 DEEPSEEK API 密钥")
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        traceback.print_exc()
        return False
    
    return True

def main():
    """Main function to run all checks"""
    print_header("API 配置诊断")
    print("开始执行检查...")
    
    checks = [
        check_credentials_file,
        test_api_key_retrieval
    ]
    
    results = []
    for i, check in enumerate(checks):
        print(f"执行检查 {i+1}/{len(checks)}: {check.__name__}")
        try:
            result = check()
            results.append(result)
            print(f"检查 {check.__name__} 完成，结果: {'通过' if result else '失败'}")
        except Exception as e:
            print(f"执行检查 {check.__name__} 时出错: {e}")
            traceback.print_exc()
            results.append(False)
    
    print_header("诊断结果")
    if all(results):
        print("✅ 所有检查通过！配置应该有效。")
    else:
        print("❌ 某些检查失败。请查看上面的错误消息。")

if __name__ == "__main__":
    try:
        print("开始执行主函数...")
        main()
        print("诊断脚本执行完成")
    except Exception as e:
        print(f"执行诊断脚本时出错: {e}")
        traceback.print_exc()
