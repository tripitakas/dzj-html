from . import task as t

handlers = [t.GetPageApi, t.GetPagesApi, t.StartTasksApi, t.UnlockTasksApi,
            t.PickCutProofTaskApi, t.PickCutReviewTaskApi, t.PickTextProofTaskApi, t.PickTextReviewTaskApi,
            t.SaveCutProofApi, t.SaveCutReviewApi,
            t.PublishTasksApi,
            ]
