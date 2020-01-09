from . import api, view

views = [
    view.TaskLobbyHandler, view.MyTaskHandler, view.TaskAdminImageHandler,
    view.PageTaskResumeHandler, view.TaskDetailHandler,
    view.PageTaskAdminHandler,
]

handlers = [
    api.PublishManyPageTasksApi, api.PublishPageTasksApi, api.PublishImportImageTasksApi,
    api.RepublishTaskApi, api.GetReadyTasksApi, api.AssignTasksApi, api.DeleteTasksApi,
    api.TaskUpdateBatchApi, api.PickTaskApi, api.ReturnTaskApi, api.FinishTaskApi,
    api.LockTaskDataApi, api.UnlockTaskDataApi, api.InitTasksForTestApi,
]
