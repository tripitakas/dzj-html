## 日志

| op_type             |     context     |  target_id |
|---------------------|:---------------:|-----------:|
| visit               | 路由地址          |            |
| submit_ocr          | OCR提交          | page_id    |
| pick_{task_type}    | 页名             |            |
| return_{task_type}  | 页名             |            |
| submit_{task_type}  | 页名             |            |
| publish_{task_type} | N个任务: 页名,页名 |            |
| save_do_{task_type} | 页名             |            |
| save_update_{task_type} | 页名         |            |
| save_edit_{task_type} | 页名           |            |
| sel_cmp_{task_type} | 页名             |            |
| withdraw_{task_type}| 页名             |            |
| reset_{task_type}   | 页名             |            |
| auto_unlock         | 页名,时间,姓名,task_type |     |
| login_no_user       | phone_or_email  |            |
| login_fail	      | phone_or_email  |            |
| login_ok	          | phone_or_email: 姓名 |        |
| logout | |
| register            | 邮箱, 手机号, 姓名 |            |
| change_user_profile | 姓名: 字段        | user_id    |
| change_role         | 姓名: 角色        | user_id    |
| reset_password      | 姓名             | user_id    |
| delete_user         | 姓名             | user_id    |
| change_password | |
| change_profile | |

每种操作的含义见 [op_type.py](../controller/op_type.py)
