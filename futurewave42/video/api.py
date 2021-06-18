from flask import request
from webargs.flaskparser import use_args

from futurewave42.video.model import Video
from futurewave42.video.schema import VideoQuerySchema, VideoSchema
from libs.base.resource import BaseResource


class VideosResource(BaseResource):
    @use_args(VideoQuerySchema)
    def get(self, args):
        videos, total = Video.get_videos_by_query(**args)
        data = VideoSchema(many=True).dump(videos).data
        return self.paginate(
            data, total, args.get('page', 1), args.get('per_page', 10))


class VideoResource(BaseResource):
    def get(self, video_id):
        video = Video.find_by_id(video_id)
        data = VideoSchema().dump(video).data
        return data
