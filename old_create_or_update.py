
def create_or_update_many(dataset, Model=Post):
    """ Create or Update if the record exists for all of the dataset list """
    print('============== Create or Update Many ====================')
    allowed_models = {Post, Insight}
    if Model not in allowed_models:
        return []
    all_results, add_count, update_count, error_set = [], 0, 0, []
    print(f'---- Initial dataset has {len(dataset)} records ----')
    # Note: initially all Models only had 1 non-pk unique field, except for unused Brand instagram_id field.
    # The following should work with multiple single column unique fields.
    columns = Model.__table__.columns
    unique = {c.name: [] for c in columns if c.unique}
    # insp = db.inspect(Model)
    print('----------------- Unique Columns -----------------------')
    pprint(unique)
    [unique[key].append(val) for ea in dataset for (key, val) in ea.items() if key in unique]
    # unique now has a key for each unique field, and a list of all the values that we want to assign those fields from the dataset
    q_to_update = Model.query.filter(or_(*[getattr(Model, key).in_(arr) for key, arr in unique.items()]))
    match = q_to_update.all()
    # match is a list of current DB records that have a unique field with a value matching the incoming dataset
    print(f'---- There seems to be {len(match)} records to update ----')
    match_dict = {}
    for key in unique.keys():
        lookup_record_by_val = {getattr(ea, key): ea for ea in match}
        match_dict[key] = lookup_record_by_val
    for data in dataset:
        # find all records in match that would collide with the values of this data
        updates = [lookup[int(data[unikey])] for unikey, lookup in match_dict.items() if int(data[unikey]) in lookup]
        # add if no collisions, update if we can, save a list of unhandled dataset elements.
        if len(updates) > 0:
            # dataset.remove(data)
            if len(updates) == 1:
                model = updates[0]
                for k, v in data.items():
                    setattr(model, k, v)
                update_count += 1
                all_results.append(model)
            else:
                print('------- Got a Multiple Match Record ------')
                data['id'] = [getattr(ea, 'id') for ea in updates]
                error_set.append(data)
        else:
            model = Model(**data)
            db.session.add(model)
            add_count += 1
            all_results.append(model)
    print('------------------------------------------------------------------------------')
    print(f'The all results has {len(all_results)} records to commit')
    print(f'This includes {update_count} updated records')
    print(f'This includes {add_count} added records')
    print(f'We were unable to handle {len(error_set)} of the incoming dataset items')
    print('------------------------------------------------------------------------------')
    db.session.commit()
    return [from_sql(ea) for ea in all_results]


def garbage_attempts_for_composite_unique_keys(dataset, Model=Post):

    if 'recorded' in columns and 'name' in columns and 'user_id' in columns:  # for each composite unique constraint
        composite = ('user_id' 'recorded', 'name')  # all columns of this constraint
        uc = [{key: val for key, val in ea.items() if key in composite} for ea in dataset]
        # array for each element of dataset, with each a dict with column: value for each column of the constraint
    for data in dataset:
        for comp_key in uc:
            val = []
            for ea in comp_key:
                val.append(data.get(ea, None))
            uc[comp_key].append(tuple(val))

    for data in dataset:
        [uc[key].append(tuple([data.get(el) for el in key])) for key in uc]

    for key, arr in uc.items():
        [arr.append(tuple([data.get(el) for el in key])) for data in dataset]

    # [uc[key].append(val) for ea in dataset for (key, val) in ea.items() ]
