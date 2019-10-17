from . import view, tripitaka, volume, sutra, reel

views = [
    view.DataPageHandler,
    view.TripitakaListHandler, view.TripitakaHandler,
    view.DataTripitakaHandler, view.DataVolumeHandler, view.DataSutraHandler, view.DataReelHandler,
]

handlers = [
    reel.ReelAddOrUpdateApi, reel.ReelUploadApi, reel.ReelDeleteApi,
    sutra.SutraAddOrUpdateApi, sutra.SutraUploadApi, sutra.SutraDeleteApi,
    volume.VolumeAddOrUpdateApi, volume.VolumeUploadApi, volume.VolumeDeleteApi,
    tripitaka.TripitakaAddOrUpdateApi, tripitaka.TripitakaUploadApi, tripitaka.TripitakaDeleteApi,
]
