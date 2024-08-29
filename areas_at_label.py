import os,sys,argparse
import SimpleITK as sitk
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description='Get label areas at a slice of a label map')
    parser.add_argument('-i', '--input', type=str, required=True, help='input image with labels to get area from')
    parser.add_argument('-r', '--reference', type=str, required=True, help='input image with label to choose the slice')
    parser.add_argument('-l', '--labels', type=int, required=True, nargs='+', action='append', help='labels to get area from')
    parser.add_argument('-c', '--centroid', type=int, required=True, help='label to get slice from')
    parser.add_argument('-o', '--output', type=str, required=True, help='output csv file with areas')
    parser.add_argument('-d', '--dimension', type=int, default=2, required=False, help='dimension to get slice from')
    parser.add_argument('-m', '--metadata', type=str, required=True, nargs=2, help='subject id and session id')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    args = parser.parse_args()

    # Load the image
    image = sitk.ReadImage(args.input)
    reference = sitk.ReadImage(args.reference)

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

    index=[0, 0, slice_idx]
    size=[image.GetSize()[0], image.GetSize()[1], 0]
    if args.dimension == 0:
        index=[slice_idx,0,0]
        size=[0,image.GetSize()[1],image.GetSize()[2]]
    elif args.dimension == 1:
        index=[0,slice_idx,0]
        size=[image.GetSize()[0],0,image.GetSize()[2]]

    slice = sitk.Extract(image, size=size, index=index)
    slice_stats = sitk.LabelShapeStatisticsImageFilter()
    slice_stats.Execute(slice)

    # flatten label list
    label_list = [ x for sublist in args.labels for x in sublist ]

    dat=[]
    for l in label_list:
        row={'subject': args.metadata[0], 'session': args.metadata[1], 'label':l, 'voxels':0, 'physical_area_mm':0.0, 'physical_volume_mm':0.0}
        if slice_stats.HasLabel(l):
            row['voxels'] = slice_stats.GetNumberOfPixels(l)
            row['physical_volume_mm'] = slice_stats.GetPhysicalSize(l)
            row['physical_area_mm'] = slice_stats.GetPhysicalSize(l) / image.GetSpacing()[args.dimension]
        dat.append(row)
    
    df = pd.DataFrame(dat)
    if args.verbose:
        print(df)

    df.to_csv(args.output, index=False)



if __name__ == '__main__':
    main()

