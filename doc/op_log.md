## 日志

| op_type             |     context     |  target_id |
|---------------------|:---------------:|-----------:|
| visit               | 路由地址          |            |
| submit_ocr          | OCR提交          | page_id    |
| submit_ocr_batch    | OCR批量提交       | count    |
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
| add_tripitaka | 新增藏数据 |
| update_tripitaka | 修改藏数据 |
| delete_tripitaka | 删除藏数据 |
| upload_tripitaka | 上传藏数据 |
| add_volume | 新增册数据 |
| update_volume | 修改册数据 |
| delete_volume | 删除册数据 |
| upload_volume | 上传册数据 |
| add_sutra | 新增经数据 |
| update_sutra | 修改经数据 |
| delete_sutra | 删除经数据 |
| upload_sutra | 上传经数据 |
| add_reel | 新增卷数据 |
| update_reel | 修改卷数据 |
| delete_reel | 删除卷数据 |
| upload_reel | 上传卷数据 |
| import_images | 导入藏经图 |

每种操作的含义见 [op_type.py](../controller/op_type.py)
