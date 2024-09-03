import os,sys,argparse
import SimpleITK as sitk
import pandas as pd

def get_stats_dict( stat_filter, i, d ):
    dat = {}
    dat['nvoxels'] = stat_filter.GetNumberOfPixels(i)
    dat['physical_volume_mm'] = stat_filter.GetPhysicalSize(i)
    dat['physical_area_mm'] = dat['physical_volume_mm'] / d
    dat['mean'] = stat_filter.GetMean(i)
    dat['median'] = stat_filter.GetMedian(i)
    dat['minimum'] = stat_filter.GetMinimum(i)
    dat['maximum'] = stat_filter.GetMaximum(i)
    dat['sd'] = stat_filter.GetStandardDeviation(i)
    dat['onborder'] = 1 # always on border for slice data
    


    return(dat)
 
def main():
    parser = argparse.ArgumentParser(description='Get label areas at a slice of a label map')
    parser.add_argument('-i', '--input', type=str, required=True, help='input CT volume')
    parser.add_argument('-s', '--segmentation', type=str, required=True, help="Labels to measure")
    parser.add_argument('-r', '--reference', type=str, required=True, help='input image with label to choose the slice')
    parser.add_argument('-l', '--labels', type=int, required=True, nargs='+', action='append', help='labels to get area from')
    parser.add_argument('-c', '--centroid', type=int, required=True, help='label to get slice from')
    parser.add_argument('-o', '--output', type=str, required=True, help='output csv file with areas')
    parser.add_argument('-d', '--dimension', type=int, default=2, required=False, help='dimension to get slice from')
    parser.add_argument('-m', '--metadata', type=str, required=True, help='subject_id session_id label_system')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    args = parser.parse_args()

    # Load the input images
    image = sitk.ReadImage(args.input)
    seg = sitk.ReadImage(args.segmentation)
    reference = sitk.ReadImage(args.reference)

    naming=os.path.basename(args.input)
    naming = naming.split('.')[0]
    parts = naming.split('_')
    series_name = parts[3:len(parts)-1]
    series_name = "_".join(series_name)
    #print(series_name)

    # Get centroid of the reference label
    label_stats = sitk.LabelShapeStatisticsImageFilter()
    label_stats.Execute(reference)
    if not label_stats.HasLabel(int(args.centroid)):
        print('Label ' + str(args.centroid) + ' for centroid not found in reference image')
        sys.exit(1)
    centroid = label_stats.GetCentroid(int(args.centroid))
    slice_idx = reference.TransformPhysicalPointToIndex(centroid)[int(args.dimension)]

    if args.verbose:
        print("Centroid (label="+str(args.centroid)+"): " + str(centroid))
        print("Slice (dim=" + str(args.dimension) + "): " + str(slice_idx))

    # Extract single slice from label image
    index=[0, 0, slice_idx]
    size=[image.GetSize()[0], image.GetSize()[1], 0]
    if args.dimension == 0:
        index=[slice_idx,0,0]
        size=[0,image.GetSize()[1],image.GetSize()[2]]
    elif args.dimension == 1:
        index=[0,slice_idx,0]
        size=[image.GetSize()[0],0,image.GetSize()[2]]
    img_slice = sitk.Extract(image, size=size, index=index)
    seg_slice = sitk.Extract(seg, size=size, index=index)

    # Get shape stats for labels in the slice
    #slice_stats = sitk.LabelShapeStatisticsImageFilter()
    slice_stats = sitk.LabelIntensityStatisticsImageFilter()
    slice_stats.Execute(seg_slice, img_slice)

    # flatten label list
    label_list = [ x for sublist in args.labels for x in sublist ]

    dat=[]
    # "id","accession","series_number","series_name","system","label","number","calculator","measure","metric","value"
    for l in label_list:
        row1={'id': parts[0], 'accession': parts[1], 'series_number': parts[2], 'series_name': series_name, 'system': args.metadata, 'label':l, 'measure': 'shape', 'metric': 'nvoxels', 'value': 0}
        row2={'id': parts[0], 'accession': parts[1], 'series_number': parts[2], 'series_name': series_name,'system': args.metadata, 'label':l, 'measure': 'shape', 'metric': 'physical_area_mm', 'value':0.0}
        row3={'id': parts[0], 'accession': parts[1], 'series_number': parts[2], 'series_name': series_name,'system': args.metadata, 'label':l, 'measure': 'shape', 'metric': 'physical_volume_mm', 'value':0.0}
        row4={'id': parts[0], 'accession': parts[1], 'series_number': parts[2], 'series_name': series_name,'system': args.metadata, 'label':l, 'measure': 'intensity', 'metric': 'mean', 'value':0.0}
        row5={'id': parts[0], 'accession': parts[1], 'series_number': parts[2], 'series_name': series_name, 'system': args.metadata, 'label':l, 'measure': 'intensity', 'metric': 'median', 'value': 0}
        row6={'id': parts[0], 'accession': parts[1], 'series_number': parts[2], 'series_name': series_name,'system': args.metadata, 'label':l, 'measure': 'intensity', 'metric': 'maximum', 'value':0.0}
        row7={'id': parts[0], 'accession': parts[1], 'series_number': parts[2], 'series_name': series_name,'system': args.metadata, 'label':l, 'measure': 'intensity', 'metric': 'minimum', 'value':0.0}
        row8={'id': parts[0], 'accession': parts[1], 'series_number': parts[2], 'series_name': series_name,'system': args.metadata, 'label':l, 'measure': 'intensity', 'metric': 'sd', 'value':0.0}
 
        if slice_stats.HasLabel(l):
            stats = get_stats_dict(slice_stats, l, image.GetSpacing()[args.dimension])
            row1['value'] = stats['nvoxels']
            row2['value'] = stats['physical_volume_mm']
            row3['value'] = stats['physical_area_mm']
            row4['value'] = stats['mean']
            row5['value'] = stats['median']
            row6['value'] = stats['maximum']
            row7['value'] = stats['minimum']
            row8['value'] = stats['sd']
        dat.append(row1)
        dat.append(row2)
        dat.append(row3)
        dat.append(row4)
        dat.append(row5)
        dat.append(row6)
        dat.append(row7)
        dat.append(row8)    

    df = pd.DataFrame(dat)
    if args.verbose:
        print(df)

    df.to_csv(args.output, index=False)



if __name__ == '__main__':
    main()

