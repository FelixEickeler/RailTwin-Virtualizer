#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

import time
import ifcopenshell
from python.modelling.oc_mapping import OCMapping
from toposort import toposort_flatten as toposort

def clone_into(dst, src, _entity):
    if isinstance(_entity, (list, tuple)):
        return [clone_into(dst, src, e) for e in _entity]
    # build tree
    entity_tree = {}
    for child in src.traverse(_entity):
        warning = set(i.id() for i in src.traverse(child)[1:] if i.id())
        entity_tree[child.id()] = warning

    # taken from https://academy.ifcopenshell.org/posts/ifcopenshell-optimizer-tutorial/
    entity_tracker = {}

    def map_value(v):
        if isinstance(v, (list, tuple)):
            # lists are recursively traversed
            return type(v)(map(map_value, v))
        elif isinstance(v, ifcopenshell.entity_instance):
            if v.id() == 0:
                # express simple types are not part of the toposort and just copied
                return dst.create_entity(v.is_a(), v[0])
            return entity_tracker[v.id()]
        else:
            # a plain python value can just be returned
            return v

    for entity_id in toposort(entity_tree):
        entity = src[entity_id]
        entity_tracker[entity_id] = dst.create_entity(entity.is_a(), *map(map_value, entity))
    return entity_tracker[_entity.id()]


def clear(file, entity):
    entity_id = entity.id()
    entity_tree = {}

    while True:
        _next = None
        skip = 0
        for child in file.traverse(entity):
            dependencies = set(i.id() for i in file.traverse(child)[1:] if i.id())
            if not dependencies:
                if skip == 0:
                    _next = child
                    break
                else:
                    skip -= 1

        if _next is None:
            break
        else:
            if not _next.is_a() == "IfcOwnerHistory":
                skip += 1
            file.remove(_next)


def swap(file, before, after):
    references = file.get_inverse(before)

    def _swap(_ref):
        # for
        # info = _ref.get_info(include_identifier=False, recursive=False)
        for i in range(len(_ref)):
            attr = _ref[i]
            if isinstance(attr, (list, tuple)):
                map(_swap, _ref)
            elif isinstance(attr, ifcopenshell.entity_instance):
                if attr == before:
                    _ref[i] = after

    for ref in references:
        _swap(ref)

        # find and swap existing

    new_ref = file.get_inverse(before)


def replace(file, before, after):
    swap(file, before, after)
    # save_delete(file, before)


class IfcFileContainer:

    def __init__(self, name, path, bounding_box, template):
        self.name = name
        self.path = path
        self.bounding_box = bounding_box
        self.property_sets = {}
        self.class_mapping = OCMapping()

        new_file = ifcopenshell.file(schema='IFC4X1')
        m_project = template.by_type("IfcProject")
        m_units = new_file.add(m_project[0].UnitsInContext)
        m_repr_context = m_project[0].RepresentationContexts[0]
        m_world_coordinate_system = m_repr_context.WorldCoordinateSystem
        m_true_north = m_repr_context.TrueNorth
        m_precision = m_repr_context.Precision
        m_coordinate_space_dimension = m_repr_context.CoordinateSpaceDimension
        m_has_coordinate_operation = m_repr_context.HasCoordinateOperation

        self.representaton_context = new_file.createIfcGeometricRepresentationContext(
            ContextType="Model",
            CoordinateSpaceDimension=m_coordinate_space_dimension,
            Precision=m_precision,
            WorldCoordinateSystem=m_world_coordinate_system,
            TrueNorth=m_true_north,
        )
        # Ask someone
        # ref = new_file.add(m_has_coordinate_operation[0])
        # rc_ref.HasCoordinateOperation = new_file.createIfcCoordinateOperation()

        # transfer IfcOwnerHistory history
        tum_address = template.create_entity("IfcAddress", Purpose="DISTRIBUTIONPOINT", Description="Arcisstraße 21, 80807 München")
        mail_address = template.create_entity("IfcAddress", Purpose="USERDEFINED", Description="felix.eickeler@tum.de", UserDefinedPurpose="ContactInformation")
        organization = template.create_entity("IfcOrganization", Name="RailTwin", Addresses=[tum_address, mail_address])
        developer_developer_developer = template.create_entity("IfcActorRole",
                                                               Role="USERDEFINED",
                                                               UserDefinedRole="Developer",
                                                               Description="How do they make roles for software applications without having any IT roles defined?")


        # change template because w/e
        person = template.create_entity("IfcPerson", FamilyName="Eickeler",
                                        GivenName="Felix",
                                        PrefixTitles=["Dipl.-Ing.(TUM)"],
                                        Roles=[developer_developer_developer],
                                        Addresses=[mail_address])

        owning_user = template.create_entity("IfcPersonAndOrganization",
                                             TheOrganization=organization,
                                             ThePerson=person)

        application = template.create_entity("IfcApplication",
                                             ApplicationDeveloper=organization,
                                             Version="22.05",
                                             ApplicationFullName="RailtwinVirtualizerAi",
                                             ApplicationIdentifier="RVAI")

        now = int(time.time())

        before = template.by_type("IfcProject")[0].OwnerHistory
        after = template.create_entity("IfcOwnerHistory",
                                       # GlobalId=ifcopenshell.guid.new(),
                                       OwningUser=owning_user,
                                       OwningApplication=application,
                                       State="READONLY",
                                       ChangeAction="ADDED",
                                       LastModifiedDate=now,
                                       LastModifyingApplication=application,
                                       LastModifyingUser=owning_user,
                                       CreationDate=now)

        swap(template, before, after)
        self.owner_history = after

        # There is a bug in ifcopenshell 0.6. It seems the tree (ids) are not getting updated and do not align with tree traverse. Therefore, manually cleanup
        # (except IfcOwnerHistory => SigSev)
        def tryer(func):
            try:
                func()
            except:
                pass

        tryer(lambda: template.remove(before.OwningUser.TheOrganization.Roles[0]))
        tryer(lambda: template.remove(before.OwningUser.TheOrganization.Addresses[0]))
        tryer(lambda: template.remove(before.OwningUser.TheOrganization))
        tryer(lambda: template.remove(before.OwningUser.ThePerson))
        # template.remove(before.OwningUser.Roles[0])
        tryer(lambda: template.remove(before.OwningUser))
        tryer(lambda: template.remove(before.OwningApplication.ApplicationDeveloper.Addresses[0]))
        tryer(lambda: template.remove(before.OwningApplication.ApplicationDeveloper.Roles[0]))
        tryer(lambda: template.remove(before.OwningApplication.ApplicationDeveloper))
        tryer(lambda: template.remove(before.OwningApplication))

        this_project = new_file.create_entity("IfcProject",
                                              GlobalId=ifcopenshell.guid.new(),
                                              OwnerHistory=after,
                                              Name=name,
                                              Description="Created By RailTwinVirtualizerAi",
                                              UnitsInContext=m_units,
                                              )
        this_project.RepresentationContexts = [self.representaton_context]
        that_ifc_site = m_project[0].IsDecomposedBy[0].RelatedObjects[0]
        if that_ifc_site.is_a("IfcSite"):
            this_ifc_site = clone_into(new_file, template, that_ifc_site)
            this_project_site_aggregate = new_file.create_entity("IfcRelAggregates",
                                                                 RelatingObject=this_project,
                                                                 RelatedObjects=[this_ifc_site])

            that_building = that_ifc_site.IsDecomposedBy[0].RelatedObjects[0]
            this_building = new_file.create_entity("IfcBuilding",
                                                   GlobalId=that_building.GlobalId,
                                                   OwnerHistory=self.owner_history,
                                                   Name=that_building.Name,
                                                   Description=that_building.Description,
                                                   ObjectType=that_building.ObjectType,
                                                   ObjectPlacement=new_file.add(that_building.ObjectPlacement),
                                                   CompositionType=that_building.CompositionType,
                                                   Representation=that_building.Representation,
                                                   LongName=that_building.LongName,
                                                   ElevationOfRefHeight=that_building.ElevationOfRefHeight,
                                                   ElevationOfTerrain=that_building.ElevationOfTerrain,
                                                   BuildingAddress=that_building.BuildingAddress
                                                   )

            this_site_building_aggregate = new_file.create_entity("IfcRelAggregates",
                                                                  RelatingObject=this_ifc_site,
                                                                  RelatedObjects=[this_building])
        self.ifc_file = new_file

    def transfer_property_set(self, from_product, to_product):
        if from_product.IsDefinedBy:
            IfcRelDefinesProperties = from_product.IsDefinedBy[0]
            # PropertySet
            if IfcRelDefinesProperties.GlobalId not in self.property_sets:
                self.property_sets[IfcRelDefinesProperties.GlobalId] = self.ifc_file.add(
                    IfcRelDefinesProperties.RelatingPropertyDefinition)

            props = {
                "OwnerHistory": self.owner_history,
                "Name": IfcRelDefinesProperties.Name,
                "Description": IfcRelDefinesProperties.Description,
                "RelatedObjects": [to_product],
                "RelatingPropertyDefinition": self.property_sets[IfcRelDefinesProperties.GlobalId]
            }
            self.ifc_file.create_entity("IfcRelDefinesByProperties", **props)

    # RelAggregates Link IfcSite to IfcProducts
    def link_products_to_site(self):
        return self.ifc_file.create_entity("IfcRelAggregates",
                                           RelatingObject=self.ifc_file.by_type("IfcBuilding")[0],
                                           RelatedObjects=self.ifc_file.by_type("IfcBuildingElement")  #
                                           )
