import os

from flask import request
from webargs.flaskparser import use_args

from futurewave42.video.model import Video
from futurewave42.video.schema import VideoSchema, VideoPutSchema, VideoQuerySchema
from libs.auth import jwt_required
from libs.base.resource import BaseResource


class AdminVideosResource(BaseResource):
    @jwt_required
    @use_args(VideoSchema)
    def post(self, args):
        video = Video.add(**args)
        data = VideoSchema().dump(video).data
        return data, 201

    @jwt_required
    @use_args(VideoQuerySchema)
    def get(self, args):
        videos, total = Video.get_videos_by_query(**args)
        data = VideoSchema(many=True).dump(videos).data
        return self.paginate(
            data, total, args.get('page', 1), args.get('per_page', 10))


class AdminVideoResource(BaseResource):
    @jwt_required
    @use_args(VideoPutSchema)
    def put(self, args, video_id):
        video = Video.find_by_id(video_id)
        video = video.update(**args)
        data = VideoSchema().dump(video).data
        return data

    @jwt_required
    def delete(self, video_id):
        video = Video.find_by_id(video_id)
        video.delete()
        return {}, 204
