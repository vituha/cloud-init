# This file is part of cloud-init. See LICENSE file for license information.
from abc import ABC, abstractmethod
import logging

from pycloudlib import EC2, GCE, Azure, OCI, LXD

from tests.integration_tests import integration_settings
from tests.integration_tests.instances import (
    IntegrationEc2Instance,
    IntegrationGceInstance,
    IntegrationAzureInstance, IntegrationInstance,
    IntegrationOciInstance,
    IntegrationLxdContainerInstance,
)

try:
    from typing import Optional
except ImportError:
    pass


log = logging.getLogger('integration_testing')


class IntegrationCloud(ABC):
    datasource = None  # type: Optional[str]
    integration_instance_cls = IntegrationInstance

    def __init__(self, settings=integration_settings):
        self.settings = settings
        self.cloud_instance = self._get_cloud_instance()
        self.image_id = self._get_initial_image()

    @abstractmethod
    def _get_cloud_instance(self):
        raise NotImplementedError

    def _get_initial_image(self):
        image_id = self.settings.OS_IMAGE
        try:
            image_id = self.cloud_instance.released_image(
                self.settings.OS_IMAGE)
        except (ValueError, IndexError):
            pass
        return image_id

    def launch(self, user_data=None, launch_kwargs=None,
               settings=integration_settings):
        if self.settings.EXISTING_INSTANCE_ID:
            log.info(
                'Not launching instance due to EXISTING_INSTANCE_ID. '
                'Instance id: %s', self.settings.EXISTING_INSTANCE_ID)
            self.instance = self.cloud_instance.get_instance(
                self.settings.EXISTING_INSTANCE_ID
            )
            return
        launch_kwargs = {
            'image_id': self.image_id,
            'user_data': user_data,
            'wait': False,
        }
        launch_kwargs.update(launch_kwargs)
        pycloudlib_instance = self.cloud_instance.launch(**launch_kwargs)
        pycloudlib_instance.wait(raise_on_cloudinit_failure=False)
        log.info('Launched instance: %s', pycloudlib_instance)
        return self.get_instance(pycloudlib_instance, settings)

    def get_instance(self, cloud_instance, settings=integration_settings):
        return self.integration_instance_cls(self, cloud_instance, settings)

    def destroy(self):
        pass

    def snapshot(self, instance):
        return self.cloud_instance.snapshot(instance, clean=True)


class Ec2Cloud(IntegrationCloud):
    datasource = 'ec2'
    integration_instance_cls = IntegrationEc2Instance

    def _get_cloud_instance(self):
        return EC2(tag='ec2-integration-test')


class GceCloud(IntegrationCloud):
    datasource = 'gce'
    integration_instance_cls = IntegrationGceInstance

    def _get_cloud_instance(self):
        return GCE(
            tag='gce-integration-test',
            project=self.settings.GCE_PROJECT,
            region=self.settings.GCE_REGION,
            zone=self.settings.GCE_ZONE,
        )


class AzureCloud(IntegrationCloud):
    datasource = 'azure'
    integration_instance_cls = IntegrationAzureInstance

    def _get_cloud_instance(self):
        return Azure(tag='azure-integration-test')

    def destroy(self):
        self.cloud_instance.delete_resource_group()


class OciCloud(IntegrationCloud):
    datasource = 'oci'
    integration_instance_cls = IntegrationOciInstance

    def _get_cloud_instance(self):
        return OCI(
            tag='oci-integration-test',
            compartment_id=self.settings.OCI_COMPARTMENT_ID
        )


class LxdContainerCloud(IntegrationCloud):
    datasource = 'lxd_container'
    integration_instance_cls = IntegrationLxdContainerInstance

    def _get_cloud_instance(self):
        return LXD(tag='lxd-integration-test')
