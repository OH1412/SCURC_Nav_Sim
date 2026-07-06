# BT 请求操作员确认已到位并选择标定点
uint8 action        # 1=Pick, 2=Place
uint8 step_index    # 当前步骤序号（从 1 开始）
string hint         # 提示文字

uint8 ACTION_PICK=1
uint8 ACTION_PLACE=2
