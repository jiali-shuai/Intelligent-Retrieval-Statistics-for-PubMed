"""加载 prompt 文件的工具"""
import os


def load_prompt(filename: str) -> str:
    """从 prompts 目录加载 txt 格式的 prompt

    Args:
        filename: prompt 文件名，如 "supervisor.txt"

    Returns:
        prompt 内容字符串
    """
    prompt_dir = os.path.join(os.path.dirname(__file__), "prompts")
    prompt_path = os.path.join(prompt_dir, filename)

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()
