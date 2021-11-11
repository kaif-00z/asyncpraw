"""Provide the WikiPage class."""
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    AsyncIterator,
    Dict,
    Optional,
    Union,
)

from ...const import API_PATH
from ...util.cache import cachedproperty
from ..listing.generator import ListingGenerator
from .base import RedditBase
from .redditor import Redditor

if TYPE_CHECKING:  # pragma: no cover
    import asyncpraw


class WikiPageModeration:
    """Provides a set of moderation functions for a WikiPage.

    For example, to add ``spez`` as an editor on the wikipage ``praw_test`` try:

    .. code-block:: python

        subreddit = await reddit.subreddit("test")
        page = await subreddit.wiki.get_page("praw_test")
        await page.mod.add("spez")

    """

    def __init__(self, wikipage: "WikiPage"):
        """Create a WikiPageModeration instance.

        :param wikipage: The wikipage to moderate.

        """
        self.wikipage = wikipage

    async def add(self, redditor: "asyncpraw.models.Redditor"):
        """Add an editor to this WikiPage.

        :param redditor: A redditor name (e.g., ``"spez"``) or :class:`~.Redditor`
            instance.

        To add ``"spez"`` as an editor on the wikipage ``"praw_test"`` try:

        .. code-block:: python

            subreddit = await reddit.subreddit("test")
            page = await subreddit.wiki.get_page("praw_test", fetch=False)
            await page.mod.add("spez")

        """
        data = {"page": self.wikipage.name, "username": str(redditor)}
        url = API_PATH["wiki_page_editor"].format(
            subreddit=self.wikipage.subreddit, method="add"
        )
        await self.wikipage._reddit.post(url, data=data)

    async def remove(self, redditor: "asyncpraw.models.Redditor"):
        """Remove an editor from this WikiPage.

        :param redditor: A redditor name (e.g., ``"spez"``) or :class:`~.Redditor`
            instance.

        To remove ``"spez"`` as an editor on the wikipage ``"praw_test"`` try:

        .. code-block:: python

            subreddit = await reddit.subreddit("test")
            page = await subreddit.wiki.get_page("praw_test", fetch=False)
            await page.mod.remove("spez")

        """
        data = {"page": self.wikipage.name, "username": str(redditor)}
        url = API_PATH["wiki_page_editor"].format(
            subreddit=self.wikipage.subreddit, method="del"
        )
        await self.wikipage._reddit.post(url, data=data)

    async def revert(self):
        """Revert a wikipage back to a specific revision.

        To revert the page ``"praw_test"`` in ``r/test`` to revision ``[ID]``, try

        .. code-block:: python

            subreddit = await reddit.subreddit("test")
            wikipage = await subreddit.wiki.get_page("praw_test")
            revision = await wikipage.revision("[ID]")
            await revision.mod.revert()

        .. note::

            When you attempt to revert the page ``config/stylesheet``, Reddit checks to
            see if the revision being reverted to passes the CSS filter. If the check
            fails, then the revision attempt will also fail, and a
            ``prawcore.Forbidden`` exception will be raised. For example, you can't
            revert to a revision that contains a link to ``url(%%PRAW%%)`` if there is
            no image named ``PRAW`` on the current stylesheet.

            Here is an example of how to look for this type of error:

            .. code-block:: python

                from asyncprawcore.exceptions import Forbidden

                try:
                    subreddit = await reddit.subreddit("test")
                    wikipage = await subreddit.wiki.get_page("config/stylesheet")
                    revision = await wikipage.revision("[ID]")
                    await revision.mod.revert()
                except Forbidden as exception:
                    try:
                        await exception.response.json()
                    except ValueError:
                        exception.response.text

            If the error occurs, the output will look something like

            .. code-block:: python

                {"reason": "INVALID_CSS", "message": "Forbidden", "explanation": "%(css_error)s"}

        """
        await self.wikipage._reddit.post(
            API_PATH["wiki_revert"].format(subreddit=self.wikipage.subreddit),
            data={
                "page": self.wikipage.name,
                "revision": self.wikipage._revision,
            },
        )

    async def settings(self) -> Dict[str, Any]:
        """Return the settings for this WikiPage."""
        url = API_PATH["wiki_page_settings"].format(
            subreddit=self.wikipage.subreddit, page=self.wikipage.name
        )
        response = await self.wikipage._reddit.get(url)
        return response["data"]

    async def update(
        self, listed: bool, permlevel: int, **other_settings: Any
    ) -> Dict[str, Any]:
        """Update the settings for this WikiPage.

        :param listed: (boolean) Show this page on page list.
        :param permlevel: (int) Who can edit this page? (0) use subreddit wiki
            permissions, (1) only approved wiki contributors for this page may edit (see
            :meth:`.WikiPageModeration.add`), (2) only mods may edit and view
        :param other_settings: Additional keyword arguments to pass.

        :returns: The updated WikiPage settings.

        To set the wikipage ``praw_test`` in ``r/test`` to mod only and disable it from
        showing in the page list, try:

        .. code-block:: python

            subreddit = await reddit.subreddit("test")
            page = await subreddit.wiki.get_page("praw_test", fetch=False)
            await page.mod.update(listed=False, permlevel=2)

        """
        other_settings.update({"listed": listed, "permlevel": permlevel})
        url = API_PATH["wiki_page_settings"].format(
            subreddit=self.wikipage.subreddit, page=self.wikipage.name
        )
        response = await self.wikipage._reddit.post(url, data=other_settings)
        return response["data"]


class WikiPage(RedditBase):
    """An individual WikiPage object.

    **Typical Attributes**

    This table describes attributes that typically belong to objects of this class.
    Since attributes are dynamically provided (see
    :ref:`determine-available-attributes-of-an-object`), there is not a guarantee that
    these attributes will always be present, nor is this list necessarily complete.

    ================= =================================================================
    Attribute         Description
    ================= =================================================================
    ``content_html``  The contents of the wiki page, as HTML.
    ``content_md``    The contents of the wiki page, as Markdown.
    ``may_revise``    A ``bool`` representing whether or not the authenticated user may
                      edit the wiki page.
    ``name``          The name of the wiki page.
    ``revision_by``   The :class:`~.Redditor` who authored this revision of the wiki
                      page.
    ``revision_date`` The time of this revision, in `Unix Time`_.
    ``subreddit``     The :class:`~.Subreddit` this wiki page belongs to.
    ================= =================================================================

    .. _unix time: https://en.wikipedia.org/wiki/Unix_time

    """

    __hash__ = RedditBase.__hash__

    @staticmethod
    async def _revision_generator(
        subreddit: "asyncpraw.models.Subreddit",
        url: str,
        generator_kwargs: Dict[str, Any],
    ) -> AsyncGenerator[
        Dict[str, Optional[Union[Redditor, "WikiPage", str, int, bool]]], None
    ]:
        async for revision in ListingGenerator(
            subreddit._reddit, url, **generator_kwargs
        ):
            if revision["author"] is not None:
                revision["author"] = Redditor(
                    subreddit._reddit, _data=revision["author"]["data"]
                )
            revision["page"] = WikiPage(
                subreddit._reddit, subreddit, revision["page"], revision["id"]
            )
            yield revision

    @cachedproperty
    def mod(self) -> WikiPageModeration:
        """Provide an instance of :class:`.WikiPageModeration`.

        For example, to add ``spez`` as an editor on the wikipage ``praw_test`` try:

        .. code-block:: python

            subreddit = await reddit.subreddit("test")
            page = await subreddit.wiki.get_page("praw_test", fetch=False)
            await page.mod.add("spez")

        """
        return WikiPageModeration(self)

    def __init__(
        self,
        reddit: "asyncpraw.Reddit",
        subreddit: "asyncpraw.models.Subreddit",
        name: str,
        revision: Optional[str] = None,
        _data: Optional[Dict[str, Any]] = None,
    ):
        """Construct an instance of the WikiPage object.

        :param revision: A specific revision ID to fetch. By default, fetches the most
            recent revision.

        """
        self.name = name
        self._revision = revision
        self.subreddit = subreddit
        super().__init__(reddit, _data=_data, _str_field=False)

    def __repr__(self) -> str:
        """Return an object initialization representation of the instance."""
        return (
            f"{self.__class__.__name__}(subreddit={self.subreddit!r},"
            f" name={self.name!r})"
        )

    def __str__(self) -> str:
        """Return a string representation of the instance."""
        return f"{self.subreddit}/{self.name}"

    def _fetch_info(self):
        return (
            "wiki_page",
            {"subreddit": self.subreddit, "page": self.name},
            {"v": self._revision} if self._revision else None,
        )

    async def _fetch_data(self):
        name, fields, params = self._fetch_info()
        path = API_PATH[name].format(**fields)
        return await self._reddit.request("GET", path, params)

    async def _fetch(self):
        data = await self._fetch_data()
        data = data["data"]
        if data["revision_by"] is not None:
            data["revision_by"] = Redditor(
                self._reddit, _data=data["revision_by"]["data"]
            )
        self.__dict__.update(data)
        self._fetched = True

    async def edit(
        self, content: str, reason: Optional[str] = None, **other_settings: Any
    ):
        """Edit this WikiPage's contents.

        :param content: The updated Markdown content of the page.
        :param reason: (Optional) The reason for the revision.
        :param other_settings: Additional keyword arguments to pass.

        For example, to replace the first wiki page of ``r/test`` with the phrase ``test
        wiki page``:

        .. code-block:: python

            subreddit = await reddit.subreddit("test")
            page = await subreddit.wiki.get_page("test", fetch=False)
            await page.edit(content="test wiki page")

        """
        other_settings.update({"content": content, "page": self.name, "reason": reason})
        await self._reddit.post(
            API_PATH["wiki_edit"].format(subreddit=self.subreddit),
            data=other_settings,
        )

    def discussions(
        self, **generator_kwargs: Any
    ) -> AsyncIterator["asyncpraw.models.Submission"]:
        """Return a :class:`.ListingGenerator` for discussions of a wiki page.

        Discussions are site-wide links to a wiki page.

        Additional keyword arguments are passed in the initialization of
        :class:`.ListingGenerator`.

        To view the titles of discussions of the page ``"praw_test"`` in ``r/test``,
        try:

        .. code-block:: python

            subreddit = await reddit.subreddit("test")
            wikipage = await subreddit.get_page("praw_test")
            async for submission in wikipage.discussions():
                print(submission.title)

        """
        return ListingGenerator(
            self._reddit,
            API_PATH["wiki_discussions"].format(
                subreddit=self.subreddit, page=self.name
            ),
            **generator_kwargs,
        )

    async def revision(self, revision: str):
        """Return a specific version of this page by revision ID.

        To view revision ``[ID]`` of ``"praw_test"`` in ``r/test``:

        .. code-block:: python

            subreddit = await reddit.subreddit("test")
            page = await subreddit.wiki.get_page("praw_test", fetch=False)
            revision = await page.revision("[ID]")

        """
        page = WikiPage(self.subreddit._reddit, self.subreddit, self.name, revision)
        await page._fetch()
        return page

    def revisions(
        self, **generator_kwargs: Union[str, int, Dict[str, str]]
    ) -> AsyncGenerator["WikiPage", None]:
        """Return a :class:`.ListingGenerator` for page revisions.

        Additional keyword arguments are passed in the initialization of
        :class:`.ListingGenerator`.

        To view the wiki revisions for ``"praw_test"`` in ``r/test`` try:

        .. code-block:: python

            subreddit = await reddit.subreddit("test")
            page = await subreddit.wiki.get_page("test_page", fetch=False)
            async for item in page.revisions():
                print(item)

        To get :class:`.WikiPage` objects for each revision:

        .. code-block:: python

            subreddit = await reddit.subreddit("test")
            page = await subreddit.wiki.get_page("test_page", fetch=False)
            async for item in page.revisions():
                print(item["page"])

        """
        url = API_PATH["wiki_page_revisions"].format(
            subreddit=self.subreddit, page=self.name
        )
        return self._revision_generator(self.subreddit, url, generator_kwargs)
