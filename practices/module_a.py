"""教材 5.1 之二：被匯入的模組（搭配 try_31_module.py 一起看）

這個檔案示範「模組的全域範圍在被 import 時會執行一次」。
下面那行 print 不在任何函式裡，所以 import 這個模組時就會印出來。
"""

print("  [module_a] 全域範圍被執行了")


def fun01():
    print("  fun01 被呼叫")


def fun02():
    print("  fun02 被呼叫")
