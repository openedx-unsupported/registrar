
DISCOVERY_PROGRAM_API_TPL = 'api/v1/programs/{}/'


def get_program_discovery_data(program_uuid, client=None):
    """
    Get a DiscoveryProgram instance, either by loading it from the cache,
    or query the Course Discovery service if it is not in the cache.

    Raises Http404 if program is not cached and Discovery returns 404
    Raises HTTPError if program is not cached and Discover returns error.
    Raises ValidationError if program is not cached and Discovery returns
        data in a format we don't like.
    """
    key = PROGRAM_CACHE_KEY_TPL.format(uuid=program_uuid)
    program = cache.get(key)
    if not isinstance(program, dict):
        program = cls.load_from_discovery(program_uuid, client)
        cache.set(key, program, PROGRAM_CACHE_TIMEOUT)
    return program


def load_from_discovery(program_uuid, client=None):
    """
    Reads the json representation of a program from the Course Discovery service.

    Raises Http404 if program is not cached and Discovery returns 404
    Raises HTTPError if Discovery returns error.
    """
    url = urljoin(
        settings.DISCOVERY_BASE_URL, 'api/v1/programs/{}/'
    ).format(
        program_uuid
    )
    try:
        program_data = make_request('GET', url, client).json()
    except HTTPError as e:
        if e.response.status_code == HTTP_404_NOT_FOUND:
            raise Http404(e)
        else:
            raise e
    return program_data

    @classmethod
    def load_from_discovery(cls, program_uuid, client=None):
        """
        Load a DiscoveryProgram instance from the Course Discovery service.

        Raises Http404 if program is not cached and Discovery returns 404
        Raises HTTPError if program is not cached AND Discovery returns error.
        """
        program_data = cls.read_from_discovery(program_uuid, client)
        return cls.from_json(program_uuid, program_data)

    @classmethod
    def from_json(cls, program_uuid, program_data):
        """
        Builds a DiscoveryProgram instance from JSON data that has been
        returned by the Course Discovery service.json
        """
        program_title = program_data.get('title')
        program_url = program_data.get('marketing_url')
        program_type = program_data.get('type')
        # this make two temporary assumptions (zwh 03/19)
        #  1. one *active* curriculum per program
        #  2. no programs are nested within a curriculum
        try:
            curriculum = next(
                c for c in program_data.get('curricula', [])
                if c.get('is_active')
            )
        except StopIteration:
            logger.exception(
                'Discovery API returned no active curricula for program {}'.format(
                    program_uuid
                )
            )
            return DiscoveryProgram(
                version=cls.class_version,
                uuid=program_uuid,
                title=program_title,
                url=program_url,
                program_type=program_type,
                active_curriculum_uuid=None,
                course_runs=[],
            )
        active_curriculum_uuid = curriculum.get("uuid")
        course_runs = [
            DiscoveryCourseRun(
                key=course_run.get('key'),
                external_key=course_run.get('external_key'),
                title=course_run.get('title'),
                marketing_url=course_run.get('marketing_url'),
            )
            for course in curriculum.get("courses", [])
            for course_run in course.get("course_runs", [])
        ]
        return DiscoveryProgram(
            version=cls.class_version,
            uuid=program_uuid,
            title=program_title,
            url=program_url,
            program_type=program_type,
            active_curriculum_uuid=active_curriculum_uuid,
            course_runs=course_runs,
        )

    def find_course_run(self, course_id):
        """
        Given a course id, return the course_run with that `key` or `external_key`

        Returns None if course run is not found in the cached program.
        """
        for course_run in self.course_runs:
            if course_id == course_run.key or course_id == course_run.external_key:
                return course_run
        return None

    def get_external_course_key(self, course_id):
        """
        Given a course ID, return the external course key for that course_run.
        The course key passed in may be an external or internal course key.


        Returns None if course run is not found in the cached program.
        """
        course_run = self.find_course_run(course_id)
        if course_run:
            return course_run.external_key
        return None

    def get_course_key(self, course_id):
        """
        Given a course ID, return the internal course ID for that course run.
        The course ID passed in may be an external or internal course key.

        Returns None if course run is not found in the cached program.
        """
        course_run = self.find_course_run(course_id)
        if course_run:
            return course_run.key
        return None
