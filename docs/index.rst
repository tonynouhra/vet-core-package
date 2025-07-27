Welcome to vet-core's documentation!
==========================================

vet-core** - A comprehensive veterinary clinic management package
with models, schemas, and database utilities.
.. note::
   **API Documentation Coverage: 97.2%** ✅

🚀 **Quick Start**
------------------

Installation::

    pip install vet-core

Basic Usage::

    from vet_core.models import User, Pet, Appointment
    from vet_core.database import get_session

    # Create a new user
    user = User(email="doctor@vetclinic.com", first_name="Dr. Smith")

📚 **Documentation**
--------------------

.. toctree::
   :maxdepth: 2
   :caption: Complete Guides:

   USAGE_GUIDE
   API_REFERENCE
   CHANGELOG

🔍 **Features**
---------------

* **User Management**: Role-based access control
* **Pet Profiles**: Complete medical history tracking
* **Appointment System**: Scheduling with conflict detection
* **Database Layer**: Async SQLAlchemy with connection pooling
* **Type Safety**: Full Pydantic validation
* **97.2% API Coverage**: Comprehensive documentation

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
