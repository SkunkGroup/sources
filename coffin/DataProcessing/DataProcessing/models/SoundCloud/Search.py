# generated by datamodel-codegen:
#   filename:  data.json
#   timestamp: 2024-10-18T00:38:01+00:00

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class PublisherMetadata(BaseModel):
    id: Optional[int] = None
    urn: Optional[str] = None
    artist: Optional[str] = None
    album_title: Optional[str] = None
    contains_music: Optional[bool] = None
    upc_or_ean: Optional[str] = None
    isrc: Optional[str] = None
    explicit: Optional[bool] = None
    p_line: Optional[str] = None
    p_line_for_display: Optional[str] = None
    writer_composer: Optional[str] = None
    release_title: Optional[str] = None
    c_line: Optional[str] = None
    c_line_for_display: Optional[str] = None


class Visual(BaseModel):
    urn: Optional[str] = None
    entry_time: Optional[int] = None
    visual_url: Optional[str] = None


class Visuals(BaseModel):
    urn: Optional[str] = None
    enabled: Optional[bool] = None
    visuals: Optional[List[Visual]] = None
    tracking: None = None


class Format(BaseModel):
    protocol: Optional[str] = None
    mime_type: Optional[str] = None


class Transcoding(BaseModel):
    url: Optional[str] = None
    preset: Optional[str] = None
    duration: Optional[int] = None
    snipped: Optional[bool] = None
    format: Optional[Format] = None
    quality: Optional[str] = None


class Media(BaseModel):
    transcodings: Optional[List[Transcoding]] = None


class Product(BaseModel):
    id: Optional[str] = None


class CreatorSubscription(BaseModel):
    product: Optional[Product] = None


class CreatorSubscription1(BaseModel):
    product: Optional[Product] = None


class Visuals1(BaseModel):
    urn: Optional[str] = None
    enabled: Optional[bool] = None
    visuals: Optional[List[Visual]] = None
    tracking: None = None


class Badges(BaseModel):
    pro: Optional[bool] = None
    creator_mid_tier: Optional[bool] = None
    pro_unlimited: Optional[bool] = None
    verified: Optional[bool] = None


class User(BaseModel):
    avatar_url: Optional[str] = None
    city: Optional[str] = None
    comments_count: Optional[int] = None
    country_code: Optional[str] = None
    created_at: Optional[str] = None
    creator_subscriptions: Optional[List[CreatorSubscription]] = None
    creator_subscription: Optional[CreatorSubscription1] = None
    description: Optional[str] = None
    followers_count: Optional[int] = None
    followings_count: Optional[int] = None
    first_name: Optional[str] = None
    full_name: Optional[str] = None
    groups_count: Optional[int] = None
    id: Optional[int] = None
    kind: Optional[str] = None
    last_modified: Optional[str] = None
    last_name: Optional[str] = None
    likes_count: Optional[int] = None
    playlist_likes_count: Optional[int] = None
    permalink: Optional[str] = None
    permalink_url: Optional[str] = None
    playlist_count: Optional[int] = None
    reposts_count: None = None
    track_count: Optional[int] = None
    uri: Optional[str] = None
    urn: Optional[str] = None
    username: Optional[str] = None
    verified: Optional[bool] = None
    visuals: Optional[Visuals1] = None
    badges: Optional[Badges] = None
    station_urn: Optional[str] = None
    station_permalink: Optional[str] = None


class CreatorSubscription2(BaseModel):
    product: Optional[Product] = None


class CreatorSubscription3(BaseModel):
    product: Optional[Product] = None


class Transcoding1(BaseModel):
    url: Optional[str] = None
    preset: Optional[str] = None
    duration: Optional[int] = None
    snipped: Optional[bool] = None
    format: Optional[Format] = None
    quality: Optional[str] = None


class Media1(BaseModel):
    transcodings: Optional[List[Transcoding1]] = None


class User1(BaseModel):
    avatar_url: Optional[str] = None
    first_name: Optional[str] = None
    followers_count: Optional[int] = None
    full_name: Optional[str] = None
    id: Optional[int] = None
    kind: Optional[str] = None
    last_modified: Optional[str] = None
    last_name: Optional[str] = None
    permalink: Optional[str] = None
    permalink_url: Optional[str] = None
    uri: Optional[str] = None
    urn: Optional[str] = None
    username: Optional[str] = None
    verified: Optional[bool] = None
    city: Optional[str] = None
    country_code: Optional[str] = None
    badges: Optional[Badges] = None
    station_urn: Optional[str] = None
    station_permalink: Optional[str] = None


class Track(BaseModel):
    artwork_url: Optional[str] = None
    caption: None = None
    commentable: Optional[bool] = None
    comment_count: Optional[int] = None
    created_at: Optional[str] = None
    description: Optional[str] = None
    downloadable: Optional[bool] = None
    download_count: Optional[int] = None
    duration: Optional[int] = None
    full_duration: Optional[int] = None
    embeddable_by: Optional[str] = None
    genre: Optional[str] = None
    has_downloads_left: Optional[bool] = None
    id: Optional[int] = None
    kind: Optional[str] = None
    label_name: Optional[str] = None
    last_modified: Optional[str] = None
    license: Optional[str] = None
    likes_count: Optional[int] = None
    permalink: Optional[str] = None
    permalink_url: Optional[str] = None
    playback_count: Optional[int] = None
    public: Optional[bool] = None
    publisher_metadata: Optional[PublisherMetadata] = None
    purchase_title: Optional[str] = None
    purchase_url: None = None
    release_date: Optional[str] = None
    reposts_count: Optional[int] = None
    secret_token: None = None
    sharing: Optional[str] = None
    state: Optional[str] = None
    streamable: Optional[bool] = None
    tag_list: Optional[str] = None
    title: Optional[str] = None
    uri: Optional[str] = None
    urn: Optional[str] = None
    user_id: Optional[int] = None
    visuals: None = None
    waveform_url: Optional[str] = None
    display_date: Optional[str] = None
    media: Optional[Media1] = None
    station_urn: Optional[str] = None
    station_permalink: Optional[str] = None
    track_authorization: Optional[str] = None
    monetization_model: Optional[str] = None
    policy: Optional[str] = None
    user: Optional[User1] = None


class CollectionItem(BaseModel):
    artwork_url: Optional[str] = None
    caption: None = None
    commentable: Optional[bool] = None
    comment_count: Optional[int] = None
    created_at: Optional[str] = None
    description: Optional[str] = None
    downloadable: Optional[bool] = None
    download_count: Optional[int] = None
    duration: Optional[int] = None
    full_duration: Optional[int] = None
    embeddable_by: Optional[str] = None
    genre: Optional[str] = None
    has_downloads_left: Optional[bool] = None
    id: Optional[int] = None
    kind: Optional[str] = None
    label_name: Optional[str] = None
    last_modified: Optional[str] = None
    license: Optional[str] = None
    likes_count: Optional[int] = None
    permalink: Optional[str] = None
    permalink_url: Optional[str] = None
    playback_count: Optional[int] = None
    public: Optional[bool] = None
    publisher_metadata: Optional[PublisherMetadata] = None
    purchase_title: Optional[str] = None
    purchase_url: None = None
    release_date: Optional[str] = None
    reposts_count: Optional[int] = None
    secret_token: None = None
    sharing: Optional[str] = None
    state: Optional[str] = None
    streamable: Optional[bool] = None
    tag_list: Optional[str] = None
    title: Optional[str] = None
    uri: Optional[str] = None
    urn: Optional[str] = None
    user_id: Optional[int] = None
    visuals: Optional[Visuals] = None
    waveform_url: Optional[str] = None
    display_date: Optional[str] = None
    media: Optional[Media] = None
    station_urn: Optional[str] = None
    station_permalink: Optional[str] = None
    track_authorization: Optional[str] = None
    monetization_model: Optional[str] = None
    policy: Optional[str] = None
    user: Optional[User] = None
    avatar_url: Optional[str] = None
    city: Optional[str] = None
    comments_count: Optional[int] = None
    country_code: Optional[str] = None
    creator_subscriptions: Optional[List[CreatorSubscription2]] = None
    creator_subscription: Optional[CreatorSubscription3] = None
    followers_count: Optional[int] = None
    followings_count: Optional[int] = None
    first_name: Optional[str] = None
    full_name: Optional[str] = None
    groups_count: Optional[int] = None
    last_name: Optional[str] = None
    playlist_likes_count: Optional[int] = None
    playlist_count: Optional[int] = None
    track_count: Optional[int] = None
    username: Optional[str] = None
    verified: Optional[bool] = None
    badges: Optional[Badges] = None
    managed_by_feeds: Optional[bool] = None
    set_type: Optional[str] = None
    is_album: Optional[bool] = None
    published_at: Optional[str] = None
    tracks: Optional[List[Track]] = None


class Facet1(BaseModel):
    value: Optional[str] = None
    count: Optional[int] = None
    filter: Optional[str] = None


class Facet(BaseModel):
    name: Optional[str] = None
    facets: Optional[List[Facet1]] = None


class SoundCloudSearch(BaseModel):
    collection: Optional[List[CollectionItem]] = None
    total_results: Optional[int] = None
    facets: Optional[List[Facet]] = None
    next_href: Optional[str] = None
    query_urn: Optional[str] = None
